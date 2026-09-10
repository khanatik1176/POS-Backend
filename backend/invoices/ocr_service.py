"""Server-side OCR fallback for images the client-side engine couldn't read.

Runs in a background thread kicked off right after a record is created, so
the HTTP response for submission never waits on this (BR-5 / FR-8). Uses a
self-hosted Tesseract via pytesseract - no external OCR provider/API key.
"""
import base64
import io
import logging

from django.conf import settings

from .field_mapping import extract_fields
from .field_template import FIELD_KEYS

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = getattr(settings, 'OCR_CONFIDENCE_THRESHOLD', 70)


def _run_tesseract(image_bytes):
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes))
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


def process_record_escalation(record):
    """Runs server OCR on this record's unreadable-locally images and
    reconciles any still-empty fields per the Section 10.4 rule."""
    pending_images = list(record.images.filter(local_read_status='unreadable', server_status='pending'))
    if not pending_images:
        return

    combined_lines = []
    any_processed = False
    for image in pending_images:
        try:
            image_bytes = base64.b64decode(image.image_data)
            lines = _run_tesseract(image_bytes)
            combined_lines.extend(lines)
            image.server_status = 'processed'
            image.server_ocr_text = '\n'.join(line['text'] for line in lines)
            any_processed = True
        except Exception:
            logger.exception('Server-side OCR failed for invoice image %s', image.id)
            image.server_status = 'failed'
        image.save(update_fields=['server_status', 'server_ocr_text', 'updated_at'])

    record.refresh_from_db(fields=['fields'])
    fields = record.fields or {}

    if any_processed:
        extracted = extract_fields(combined_lines)
        for key in FIELD_KEYS:
            field = fields.get(key) or {}
            if field.get('origin') != 'server-pending':
                continue
            match = extracted.get(key)
            if match and match['confidence'] >= CONFIDENCE_THRESHOLD:
                fields[key] = {'value': match['value'], 'origin': 'server-filled', 'confidence': match['confidence']}
            else:
                fields[key] = {'value': field.get('value', ''), 'origin': 'server-unresolved', 'confidence': None}
    else:
        for key in FIELD_KEYS:
            field = fields.get(key) or {}
            if field.get('origin') == 'server-pending':
                fields[key] = {'value': field.get('value', ''), 'origin': 'server-unresolved', 'confidence': None}

    record.fields = fields
    record.has_pending_server_review = record.images.filter(server_status='pending').exists()
    record.notified = False
    record.save(update_fields=['fields', 'has_pending_server_review', 'notified', 'updated_at'])
