"""Label/regex based field extraction from OCR line output.

Mirrors the client-side extraction in the frontend's lib/ocrFieldMapping.ts
so server-side reprocessing (for images the browser couldn't read) applies
the same heuristics. Kept intentionally simple/regex-based per the BRD.
"""
import re

LABEL_PATTERNS = {
    'invoice_number': [r'invoice\s*(no\.?|number|#)', r'receipt\s*(no\.?|number|#)'],
    'invoice_date': [r'invoice\s*date', r'date\s*of\s*issue'],
    'due_date': [r'due\s*date', r'payment\s*due'],
    'subtotal': [r'sub[\s-]*total'],
    'tax_amount': [r'\bvat\b', r'\btax\b', r'\bgst\b'],
    'total_amount': [r'\bgrand\s*total\b', r'\btotal\s*due\b', r'(?<!sub)(?<!sub )\btotal\b'],
    'payment_method': [r'payment\s*method', r'paid\s*via', r'paid\s*by'],
    'currency': [r'\bcurrency\b'],
}

AMOUNT_RE = re.compile(r'([€£$₹৳]|[A-Z]{3})?\s?([0-9][0-9,]*\.?[0-9]{0,2})')
DATE_RE = re.compile(r'(\d{1,4}[/-]\d{1,2}[/-]\d{1,4})')
LABEL_VALUE_RE = re.compile(r'[:\-]\s*(.+)$')
CURRENCY_SYMBOLS = {'$': 'USD', '€': 'EUR', '£': 'GBP', '₹': 'INR', '৳': 'BDT'}
CURRENCY_CODE_RE = re.compile(r'\b(USD|EUR|GBP|INR|BDT)\b', re.IGNORECASE)


def _extract_value(key, text):
    if key in ('subtotal', 'tax_amount', 'total_amount'):
        match = AMOUNT_RE.search(text)
        return match.group(2).replace(',', '') if match else None
    if key in ('invoice_date', 'due_date'):
        match = DATE_RE.search(text)
        return match.group(1) if match else None
    if key == 'currency':
        for symbol, code in CURRENCY_SYMBOLS.items():
            if symbol in text:
                return code
        match = CURRENCY_CODE_RE.search(text)
        return match.group(1).upper() if match else None
    match = LABEL_VALUE_RE.search(text)
    if match:
        return match.group(1).strip()
    return None


def extract_fields(ocr_lines):
    """ocr_lines: list of {'text': str, 'confidence': float (0-100)}.

    Returns {field_key: {'value': str, 'confidence': float}} for fields it
    could confidently locate via a label match.
    """
    results = {}
    for key, patterns in LABEL_PATTERNS.items():
        for line in ocr_lines:
            text = line.get('text', '')
            if not text:
                continue
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                value = _extract_value(key, text)
                if value:
                    results[key] = {'value': value, 'confidence': line.get('confidence', 0)}
                    break

    if 'vendor_name' not in results:
        all_patterns = [p for patterns in LABEL_PATTERNS.values() for p in patterns]
        for line in ocr_lines:
            text = (line.get('text') or '').strip()
            if len(text) < 3 or not re.search(r'[A-Za-z]{3,}', text):
                continue
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in all_patterns):
                continue
            results['vendor_name'] = {'value': text, 'confidence': line.get('confidence', 0)}
            break

    return results
