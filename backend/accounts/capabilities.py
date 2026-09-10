"""Registry of pages and actions that roles can be granted.

Each page has an implicit `<page>.view` action controlling whether the page
is visible at all, plus zero or more finer-grained action keys (e.g. "create
an order") that only matter once the page itself is visible. Superusers
bypass this registry entirely (see accounts/permissions.py).
"""

CAPABILITY_REGISTRY = [
    {
        'page': 'dashboard',
        'label': 'Dashboard',
        'view_action': 'dashboard.view',
        'actions': [],
    },
    {
        'page': 'orders',
        'label': 'Orders',
        'view_action': 'orders.view',
        'actions': [
            {'key': 'orders.create', 'label': 'Create order'},
            {'key': 'orders.verify', 'label': 'Verify order'},
            {'key': 'orders.deliver', 'label': 'Deliver order'},
            {'key': 'orders.export', 'label': 'Download Excel export'},
        ],
    },
    {
        'page': 'ocr',
        'label': 'Invoice OCR',
        'view_action': 'ocr.view',
        'actions': [
            {'key': 'ocr.create', 'label': 'New invoice entry'},
            {'key': 'ocr.export', 'label': 'Download Excel export'},
        ],
    },
]


def _all_action_keys():
    keys = set()
    for page in CAPABILITY_REGISTRY:
        keys.add(page['view_action'])
        for action in page['actions']:
            keys.add(action['key'])
    return keys


ALL_ACTION_KEYS = _all_action_keys()
