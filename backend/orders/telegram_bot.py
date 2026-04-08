import json
import logging
from urllib import request

from django.conf import settings

logger = logging.getLogger(__name__)


TELEGRAM_API_TIMEOUT = 10


def _telegram_api_call(method, payload):
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        return None

    url = f"https://api.telegram.org/bot{token}/{method}"
    req = request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with request.urlopen(req, timeout=TELEGRAM_API_TIMEOUT) as response:
        data = response.read().decode('utf-8')
        return json.loads(data)


def send_order_for_review(order, amount=None):
    enabled = getattr(settings, 'TELEGRAM_BOT_ENABLED', False)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '')
    if not enabled or not chat_id:
        return False

    amount_text = str(amount) if amount is not None else 'N/A'
    payment_medium = order.payment_medium.name if order.payment_medium else 'N/A'

    text = (
        'New Order Pending Review\n\n'
        f'Order ID: {order.id}\n'
        f'Reference No: {order.reference_number}\n'
        f'Amount: {amount_text}\n'
        f'Payment Medium: {payment_medium}\n'
        f'Customer Name: {order.customer_name}\n'
        f'URL: {order.url}'
    )

    payload = {
        'chat_id': chat_id,
        'text': text,
        'reply_markup': {
            'inline_keyboard': [
                [
                    {'text': 'Approve', 'callback_data': f'ord|{order.id}|ap'},
                    {'text': 'Decline', 'callback_data': f'ord|{order.id}|dc'},
                ]
            ]
        },
    }

    try:
        response = _telegram_api_call('sendMessage', payload)
        return bool(response and response.get('ok'))
    except Exception:
        logger.exception('Failed to send Telegram review message for order %s', order.id)
        return False


def answer_callback_query(callback_query_id, text):
    try:
        _telegram_api_call('answerCallbackQuery', {
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': False,
        })
    except Exception:
        logger.exception('Failed to answer Telegram callback query')


def edit_message(chat_id, message_id, text):
    try:
        _telegram_api_call('editMessageText', {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
        })
    except Exception:
        logger.exception('Failed to edit Telegram message')
