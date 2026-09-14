"""Server-side OCR fallback for images the client-side engine couldn't read.

Runs in a background thread kicked off right after a record is created, so
the HTTP response for submission never waits on this (BR-5 / FR-8). Uses a
self-hosted Tesseract via pytesseract - no external OCR provider/API key.
"""
import base64
import io
import logging

from django.conf import settings

from .mobile_money_field_mapping import extract_fields as extract_mobile_money_fields
from .mobile_money_field_mapping import merge_extracted_fields
from .record_types import FIELD_KEYS_BY_TYPE, extract_fields_for

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = getattr(settings, 'OCR_CONFIDENCE_THRESHOLD', 70)

# Mobile-money receipts (bKash/Nagad/Rocket) are frequently in Bengali script;
# invoices are generally English. Ask Tesseract for both scripts in one pass
# rather than branching per record type. Falls back to English-only if the
# Bengali language pack (ben.traineddata) isn't installed on this host.
OCR_LANGUAGES = 'eng+ben'

OCR_MIN_DIMENSION = 1600
OCR_MAX_UPSCALE = 2


def _prepare_image_for_ocr(image):
    """Upscale + grayscale small phone screenshots for clearer TrxID glyphs."""
    from PIL import Image, ImageOps

    image = image.convert('RGB')
    max_dim = max(image.size)
    if max_dim < OCR_MIN_DIMENSION:
        scale = min(OCR_MAX_UPSCALE, OCR_MIN_DIMENSION / max_dim)
        # Keep at least 2x for typical ~500–1100px receipt screenshots.
        scale = max(scale, 2.0) if max_dim < 1200 else scale
        image = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.Resampling.LANCZOS,
        )
    return ImageOps.grayscale(image)


def _lines_from_pil_image(image):
    import pytesseract

    try:
        data = pytesseract.image_to_data(image, lang=OCR_LANGUAGES, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractError:
        logger.warning('Tesseract language pack "%s" unavailable, falling back to English only', OCR_LANGUAGES)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    lines = {}
    for i, text in enumerate(data['text']):
        if not text.strip():
            continue
        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        raw_conf = data['conf'][i]
        try:
            conf = float(raw_conf)
        except (TypeError, ValueError):
            conf = 0.0
        entry = lines.setdefault(key, {'words': [], 'confidences': []})
        entry['words'].append(text)
        entry['confidences'].append(max(conf, 0.0))

    ocr_lines = []
    for entry in lines.values():
        confidences = entry['confidences']
        ocr_lines.append({
            'text': ' '.join(entry['words']),
            'confidence': sum(confidences) / len(confidences) if confidences else 0.0,
        })
    return ocr_lines


def _run_tesseract(image_bytes):
    """Dual-pass OCR: original color + upscaled grayscale.

    English history-list rows keep clearer "TrxID" labels on the raw pass;
    Bengali grids need the upscaled grayscale pass for the bottom cells.
    """
    from PIL import Image

    original = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    raw_lines = _lines_from_pil_image(original)
    prepared_lines = _lines_from_pil_image(_prepare_image_for_ocr(original))
    # Prefer prepared lines in the combined text dump (usually denser), but
    # keep raw lines too so label-sensitive extractors can still match.
    combined = list(prepared_lines)
    combined.extend(raw_lines)
    return combined, raw_lines, prepared_lines


def _extract_from_image_bytes(image_bytes, record_type):
    combined, raw_lines, prepared_lines = _run_tesseract(image_bytes)
    if record_type == 'mobile_money_receipt':
        extracted = merge_extracted_fields(
            extract_mobile_money_fields(raw_lines),
            extract_mobile_money_fields(prepared_lines),
        )
    else:
        extracted = extract_fields_for(record_type, combined)
    return combined, extracted


def process_record_escalation(record):
    """Runs server OCR on this record's unreadable-locally images and
    reconciles any still-empty fields per the Section 10.4 rule."""
    pending_images = list(record.images.filter(local_read_status='unreadable', server_status='pending'))
    if not pending_images:
        return

    merged_extracted = {}
    any_processed = False
    for image in pending_images:
        try:
            image_bytes = base64.b64decode(image.image_data)
            lines, extracted = _extract_from_image_bytes(image_bytes, record.record_type)
            if record.record_type == 'mobile_money_receipt':
                merged_extracted = merge_extracted_fields(merged_extracted, extracted)
            else:
                # Fall back to the previous combined-line behaviour for invoices.
                from .record_types import extract_fields_for as _extract
                merged_extracted = _extract(record.record_type, lines)
            image.server_status = 'processed'
            image.server_ocr_text = '\n'.join(line['text'] for line in lines)
            any_processed = True
        except Exception:
            logger.exception('Server-side OCR failed for invoice image %s', image.id)
            image.server_status = 'failed'
        image.save(update_fields=['server_status', 'server_ocr_text', 'updated_at'])

    record.refresh_from_db(fields=['fields'])
    fields = record.fields or {}
    field_keys = FIELD_KEYS_BY_TYPE[record.record_type]

    if any_processed:
        extracted = merged_extracted
        for key in field_keys:
            field = fields.get(key) or {}
            if field.get('origin') != 'server-pending':
                continue
            match = extracted.get(key)
            if match and match['confidence'] >= CONFIDENCE_THRESHOLD:
                fields[key] = {'value': match['value'], 'origin': 'server-filled', 'confidence': match['confidence']}
            else:
                fields[key] = {'value': field.get('value', ''), 'origin': 'server-unresolved', 'confidence': None}
    else:
        for key in field_keys:
            field = fields.get(key) or {}
            if field.get('origin') == 'server-pending':
                fields[key] = {'value': field.get('value', ''), 'origin': 'server-unresolved', 'confidence': None}

    record.fields = fields
    record.has_pending_server_review = record.images.filter(server_status='pending').exists()
    record.notified = False
    record.save(update_fields=['fields', 'has_pending_server_review', 'notified', 'updated_at'])
