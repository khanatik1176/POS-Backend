"""Label/regex based field extraction for mobile-money (bKash/Nagad/Rocket
style) "Send Money" receipt screenshots.

Mirrors the client-side extraction in the frontend's
lib/mobileMoneyFieldMapping.ts so server-side reprocessing (for images the
browser couldn't read) applies the same heuristics.
"""
import re

LABEL_PATTERNS = {
    # OCR often garbles "TrxID" / "Transaction ID" (I→l, I→1, missing spaces).
    # "1110" is a common grayscale-OCR reading of "TrxID".
    'transaction_id': [
        r'trx[\s.:_-]*[il1|]d',
        r'transact[a-z]*[\s.:_-]*[il1|]d',
        r'ট্রানজেকশন\s*আই[ডদভ]ি',
        r'\b1110\b',
    ],
    'phone_number': [r'একাউন্ট', r'\baccount\b'],
    'transaction_datetime': [r'\btime\b', r'সম[য়য়]'],
    'amount': [r'\bamount\b', r'পরিমাণ'],
    'charge': [r'\bcharge\b', r'চার্জ'],
    'total_amount': [r'\btotal\b'],
    'reference_name': [r'\breference\b', r'রেফারেন্স'],
}

BENGALI_DIGIT_MAP = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')

# Strict: letter+digit mix. Loose: used after an explicit TrxID label when OCR
# turns every "1" into "I" (e.g. DIA1D1BOVB → DIAIDIBOVB).
TRANSACTION_ID_STRICT_RE = re.compile(
    r'\b(?=[A-Za-z0-9]{6,14}\b)(?=[A-Za-z0-9]*[0-9])(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]+\b'
)
TRANSACTION_ID_LOOSE_RE = re.compile(r'\b[A-Za-z][A-Za-z0-9]{5,13}\b')
PHONE_RE = re.compile(r'01[3-9]\d(?:[-\s]?\d){7}')
DATETIME_LONG_RE = re.compile(r'\d{1,2}\s+[A-Za-z]+\s+\d{4},?\s*\d{1,2}:\d{2}\s*[APap][Mm]')
DATETIME_COMPACT_RE = re.compile(r'\d{1,2}:\d{2}\s*[APap][Mm]\s+\d{1,2}/\d{1,2}/\d{2,4}')
DATETIME_COMPACT_DATE_FIRST_RE = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*[APap][Mm]')
CURRENCY_VALUE_RE = re.compile(r'(?:[-−]\s*)?(?:৳|%|Tk\.?|টাকা)?\s*([0-9][0-9,]*\.?[0-9]{0,2})\s*(?:৳|%|Tk\.?|টাকা)?')
NO_CHARGE_RE = re.compile(r'no\s*charge', re.IGNORECASE)
COPY_ICON_JUNK_RE = re.compile(r'\[[A-Za-z0-9]{0,3}\]?')
NAME_TOKEN_RE = re.compile(r'[A-Za-z][A-Za-z .]{1,29}')

# Regex-validated extractions are trustworthy even when Tesseract confidence
# is low — raise them above the UI threshold so the form actually fills.
FIELD_MIN_CONFIDENCE = 80

NOISE_SUBSTRINGS = [
    'send money', 'successful', 'call', 'message', 'share', 'back to home',
    'enable auto pay', 'auto pay', 'reward points', 'new balance', 'you have',
    'you have earned', 'bkash', 'nagad', 'rocket', 'to use your points', 'check your',
    'সেন্ড মানি', 'স্যান্ড মানি', 'বন্ধ', 'শেয়ার', 'একাউন্ট', 'সময়', 'সময়', 'পরিমাণ', 'চার্জ',
    'ট্রানজেকশন', 'রেফারেন্স', 'ইনবক্স', 'নোটিফিকেশন', 'ফিল্টার', 'লেনদেন',
]
NAME_CANDIDATE_RE = re.compile(r'^[A-Za-z][A-Za-z .]{2,29}$')

ALL_LABEL_PATTERNS = [p for patterns in LABEL_PATTERNS.values() for p in patterns]


TRANSACTION_ID_BLOCKLIST = {
    'transaction', 'reference', 'successful', 'balance', 'amount', 'charge',
    'total', 'sendmoney', 'bkash', 'nagad', 'rocket', 'enable', 'share',
}


def _normalize_digits(text):
    return text.translate(BENGALI_DIGIT_MAP) if text else text


def _is_plausible_transaction_id(value):
    if not value or not (6 <= len(value) <= 14) or not value.isalnum():
        return False
    if value.lower() in TRANSACTION_ID_BLOCKLIST:
        return False
    if any(c.isdigit() for c in value):
        return True
    # All-letter OCR of digit-containing IDs (1→I) is usually ALL CAPS.
    return value.isupper() and value.isalpha()


def _normalize_datetime(raw):
    text = raw.strip()
    time_first = re.match(
        r'^(\d{1,2}:\d{2}\s*[APap][Mm])\s+(\d{1,2}/\d{1,2}/\d{2,4})$',
        text,
    )
    if time_first:
        return f'{time_first.group(2)} {time_first.group(1)}'
    return text


def _extract_datetime(text):
    match = DATETIME_LONG_RE.search(text)
    if match:
        return match.group(0).strip()
    match = DATETIME_COMPACT_RE.search(text) or DATETIME_COMPACT_DATE_FIRST_RE.search(text)
    return _normalize_datetime(match.group(0)) if match else None


def _normalize_currency_amount(value):
    if re.fullmatch(r'[68]\d{3}\.\d{2}', value):
        stripped = value[1:]
        whole = int(stripped.split('.')[0])
        if 1 <= whole <= 999:
            return stripped
    return value


def _extract_currency_values(text):
    return [_normalize_currency_amount(match.group(1).replace(',', '')) for match in CURRENCY_VALUE_RE.finditer(text)]


def _is_name_candidate(text):
    text = text.strip()
    if not NAME_CANDIDATE_RE.match(text):
        return False
    if len(text) < 3:
        return False
    if re.fullmatch(r'[A-Z]{1,3}', text):
        return False
    # All-caps tokens of trx-id length are IDs, not person names.
    if re.fullmatch(r'[A-Z]{6,14}', text):
        return False
    lowered = text.lower()
    if any(noise in lowered for noise in NOISE_SUBSTRINGS):
        return False
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in ALL_LABEL_PATTERNS):
        return False
    return True


def _clean_reference_candidate(text):
    text = text.strip()
    parts = text.split()
    while parts and len(parts[0]) <= 2:
        parts = parts[1:]
    while parts and len(parts[-1]) <= 2:
        parts = parts[:-1]
    return ' '.join(parts).strip()


def _extract_reference_name(raw_text):
    remainder = _normalize_digits(raw_text)
    for pattern in ALL_LABEL_PATTERNS:
        remainder = re.sub(pattern, '', remainder, flags=re.IGNORECASE)
    # Only strip strict (digit-containing) trx IDs — loose matching would
    # delete real names like "Nafisha".
    remainder = TRANSACTION_ID_STRICT_RE.sub('', remainder)
    remainder = PHONE_RE.sub('', remainder)
    remainder = DATETIME_LONG_RE.sub('', remainder)
    remainder = DATETIME_COMPACT_RE.sub('', remainder)
    remainder = DATETIME_COMPACT_DATE_FIRST_RE.sub('', remainder)
    remainder = CURRENCY_VALUE_RE.sub('', remainder)
    remainder = COPY_ICON_JUNK_RE.sub('', remainder)
    remainder = remainder.strip(' :–-_|').strip()
    remainder = _clean_reference_candidate(remainder)
    if _is_name_candidate(remainder):
        return remainder
    for token in NAME_TOKEN_RE.findall(remainder):
        trimmed = _clean_reference_candidate(token)
        if _is_name_candidate(trimmed):
            return trimmed
    return None


def _normalize_transaction_id(value):
    value = value.strip(' >|')
    value = re.sub(r'I([A-Z])$', r'1\1', value)
    return value


def _strip_known_labels(text):
    cleaned = text
    for pattern in ALL_LABEL_PATTERNS:
        cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
    return cleaned


def _extract_transaction_id(text, loose=False):
    text = _normalize_digits(text)
    match = TRANSACTION_ID_STRICT_RE.search(text)
    if match and _is_plausible_transaction_id(match.group(0)):
        return _normalize_transaction_id(match.group(0))
    if loose:
        for match in TRANSACTION_ID_LOOSE_RE.finditer(text):
            candidate = _normalize_transaction_id(match.group(0))
            if _is_plausible_transaction_id(candidate):
                return candidate
    return None


def _extract_value(key, text, labeled=False):
    text = _normalize_digits(text)
    if key == 'transaction_id':
        # Strip labels first so "Time Transaction ID" doesn't yield "Transaction".
        return _extract_transaction_id(_strip_known_labels(text), loose=labeled)
    if key == 'phone_number':
        match = PHONE_RE.search(text)
        return re.sub(r'\D', '', match.group(0)) if match else None
    if key == 'transaction_datetime':
        return _extract_datetime(text)
    if key in ('amount', 'charge', 'total_amount'):
        if key == 'charge' and NO_CHARGE_RE.search(text):
            return '0'
        values = _extract_currency_values(text)
        if not values:
            return None
        # Prefer the primary money amount; avoid trailing OCR crumbs like "1".
        if key == 'total_amount':
            return max(values, key=lambda value: float(value or 0))
        if key == 'amount':
            return values[0]
        return values[1] if len(values) > 1 else values[0]
    if key == 'reference_name':
        return _extract_reference_name(text)
    return None


def _with_boosted_confidence(confidence):
    return max(confidence or 0, FIELD_MIN_CONFIDENCE)


def _score_transaction_id(value):
    """Prefer IDs that still contain digits after OCR."""
    if not value:
        return 0
    return (2 if any(c.isdigit() for c in value) else 1, len(value))


def merge_extracted_fields(*results):
    """Merge multiple extract_fields() passes (e.g. raw + preprocessed OCR)."""
    merged = {}
    for result in results:
        for key, item in (result or {}).items():
            existing = merged.get(key)
            if not existing:
                merged[key] = item
                continue
            if key == 'transaction_id':
                if _score_transaction_id(item['value']) > _score_transaction_id(existing['value']):
                    merged[key] = item
                elif (
                    _score_transaction_id(item['value']) == _score_transaction_id(existing['value'])
                    and item.get('confidence', 0) > existing.get('confidence', 0)
                ):
                    merged[key] = item
            elif item.get('confidence', 0) > existing.get('confidence', 0):
                merged[key] = item
    return merged


def extract_fields(ocr_lines):
    """ocr_lines: list of {'text': str, 'confidence': float (0-100)}."""
    results = {}
    line_count = len(ocr_lines)
    for key, patterns in LABEL_PATTERNS.items():
        for i, line in enumerate(ocr_lines):
            text = line.get('text', '')
            if not text:
                continue
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                value = _extract_value(key, text, labeled=True)
                confidence = line.get('confidence', 0)
                if not value and i + 1 < line_count:
                    next_line = ocr_lines[i + 1]
                    next_text = next_line.get('text', '')
                    if next_text:
                        next_value = _extract_value(key, next_text, labeled=True)
                        if next_value:
                            value = next_value
                            confidence = max(confidence, next_line.get('confidence', 0))
                if value:
                    results[key] = {'value': value, 'confidence': _with_boosted_confidence(confidence)}
                    break

    if 'transaction_id' not in results:
        for line in ocr_lines:
            value = _extract_transaction_id(line.get('text', ''), loose=False)
            if value:
                results['transaction_id'] = {
                    'value': value,
                    'confidence': _with_boosted_confidence(line.get('confidence', 0)),
                }
                break

    if 'phone_number' not in results:
        for line in ocr_lines:
            text = _normalize_digits(line.get('text', ''))
            match = PHONE_RE.search(text)
            if match:
                results['phone_number'] = {
                    'value': re.sub(r'\D', '', match.group(0)),
                    'confidence': _with_boosted_confidence(line.get('confidence', 0)),
                }
                break

    if 'transaction_datetime' not in results:
        for line in ocr_lines:
            value = _extract_datetime(_normalize_digits(line.get('text', '')))
            if value:
                results['transaction_datetime'] = {
                    'value': value,
                    'confidence': _with_boosted_confidence(line.get('confidence', 0)),
                }
                break

    if not any(k in results for k in ('amount', 'charge', 'total_amount')):
        for line in ocr_lines:
            text = _normalize_digits(line.get('text', ''))
            if (
                PHONE_RE.search(text)
                or DATETIME_LONG_RE.search(text)
                or DATETIME_COMPACT_RE.search(text)
                or DATETIME_COMPACT_DATE_FIRST_RE.search(text)
            ):
                continue
            if TRANSACTION_ID_STRICT_RE.search(text):
                continue
            values = _extract_currency_values(text)
            if values:
                results['amount'] = {
                    'value': values[0],
                    'confidence': _with_boosted_confidence(line.get('confidence', 0)),
                }
                break

    if 'reference_name' not in results or not results['reference_name']['value']:
        for line in ocr_lines:
            text = line.get('text') or ''
            if not TRANSACTION_ID_STRICT_RE.search(_normalize_digits(text)) and not TRANSACTION_ID_LOOSE_RE.search(text):
                continue
            name = _extract_reference_name(text)
            if name:
                results['reference_name'] = {
                    'value': name,
                    'confidence': _with_boosted_confidence(line.get('confidence', 0)),
                }
                break

    if 'reference_name' not in results or not results['reference_name']['value']:
        for line in ocr_lines:
            text = (line.get('text') or '').strip()
            if _is_name_candidate(text):
                results['reference_name'] = {
                    'value': text,
                    'confidence': _with_boosted_confidence(line.get('confidence', 0)),
                }
                break

    return results
