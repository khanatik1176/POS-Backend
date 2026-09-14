"""Registry mapping a record's type to its field template and extractor.

Keeps invoices/field_mapping.py (generic vendor invoices) and
invoices/mobile_money_field_mapping.py (bKash/Nagad/Rocket "Send Money"
receipts) as independent, side-by-side field sets sharing the same
InvoiceRecord/InvoiceImage storage and OCR pipeline.
"""
from . import field_mapping, mobile_money_field_mapping
from .field_template import FIELD_TEMPLATE
from .mobile_money_field_template import MOBILE_MONEY_FIELD_TEMPLATE

INVOICE = 'invoice'
MOBILE_MONEY_RECEIPT = 'mobile_money_receipt'

RECORD_TYPE_CHOICES = [
    (INVOICE, 'Invoice'),
    (MOBILE_MONEY_RECEIPT, 'Mobile Money Receipt'),
]
RECORD_TYPES = [choice[0] for choice in RECORD_TYPE_CHOICES]

FIELD_TEMPLATES = {
    INVOICE: FIELD_TEMPLATE,
    MOBILE_MONEY_RECEIPT: MOBILE_MONEY_FIELD_TEMPLATE,
}

FIELD_KEYS_BY_TYPE = {
    record_type: {item['key'] for item in template}
    for record_type, template in FIELD_TEMPLATES.items()
}

EXTRACTORS = {
    INVOICE: field_mapping.extract_fields,
    MOBILE_MONEY_RECEIPT: mobile_money_field_mapping.extract_fields,
}


def extract_fields_for(record_type, ocr_lines):
    extractor = EXTRACTORS.get(record_type, field_mapping.extract_fields)
    return extractor(ocr_lines)
