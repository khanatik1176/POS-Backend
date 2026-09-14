MOBILE_MONEY_FIELD_TEMPLATE = [
    {'key': 'transaction_id', 'label': 'Transaction ID', 'type': 'text'},
    {'key': 'phone_number', 'label': 'Phone Number', 'type': 'text'},
    {'key': 'transaction_datetime', 'label': 'Date & Time', 'type': 'text'},
    {'key': 'amount', 'label': 'Amount', 'type': 'currency'},
    {'key': 'charge', 'label': 'Charge / Fee', 'type': 'currency'},
    {'key': 'total_amount', 'label': 'Total', 'type': 'currency'},
    {'key': 'reference_name', 'label': 'Recipient / Reference', 'type': 'text'},
]

MOBILE_MONEY_FIELD_KEYS = {item['key'] for item in MOBILE_MONEY_FIELD_TEMPLATE}
