FIELD_TEMPLATE = [
    {'key': 'vendor_name', 'label': 'Vendor / Merchant Name', 'type': 'text'},
    {'key': 'invoice_number', 'label': 'Invoice / Receipt Number', 'type': 'text'},
    {'key': 'invoice_date', 'label': 'Invoice Date', 'type': 'date'},
    {'key': 'due_date', 'label': 'Due Date', 'type': 'date'},
    {'key': 'currency', 'label': 'Currency', 'type': 'text'},
    {'key': 'payment_method', 'label': 'Payment Method', 'type': 'text'},
    {'key': 'subtotal', 'label': 'Subtotal', 'type': 'currency'},
    {'key': 'tax_amount', 'label': 'Tax / VAT Amount', 'type': 'currency'},
    {'key': 'total_amount', 'label': 'Total Amount', 'type': 'currency'},
]

FIELD_KEYS = {item['key'] for item in FIELD_TEMPLATE}

LINE_ITEM_FIELDS = ['description', 'quantity', 'unit_price', 'amount']

ORIGIN_CHOICES = (
    'auto',
    'manual',
    'empty',
    'server-pending',
    'server-filled',
    'server-unresolved',
)
