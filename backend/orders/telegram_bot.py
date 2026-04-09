import json
import logging
from urllib import request

from django.conf import settings

logger = logging.getLogger(__name__)


def _call_telegram_api(method, payload):
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        return None

    url = f'https://api.telegram.org/bot{token}/{method}'
    req = request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with request.urlopen(req, timeout=10) as response:
        body = response.read().decode('utf-8')
        return json.loads(body)


def send_order_review_message(order, amount=None):
    enabled = getattr(settings, 'TELEGRAM_BOT_ENABLED', False)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '')
    if not enabled or not chat_id:
        return False

    payment_medium = order.payment_medium.name if order.payment_medium else 'N/A'
    amount_text = str(amount) if amount not in (None, '') else 'N/A'

    payload = {
        'chat_id': chat_id,
        'text': (
            'New Order Pending Review\n\n'
            f'Reference No: {order.reference_number}\n'
            f'Amount: {amount_text}\n'
            f'Payment Medium: {payment_medium}\n'
            f'Customer Name: {order.customer_name}\n'
            f'URL: {order.url}'
        ),
        'reply_markup': {
            'inline_keyboard': [
                [
                    {'text': 'Verified', 'callback_data': f'ord|{order.id}|verified'},
                    {'text': 'Declined', 'callback_data': f'ord|{order.id}|declined'},
                ]
            ]
        },
    }

    try:
        response = _call_telegram_api('sendMessage', payload)
        return bool(response and response.get('ok'))
    except Exception:
        logger.exception('Failed to send Telegram review message for order %s', order.id)
        return False


def answer_callback(callback_query_id, text):
    if not callback_query_id:
        return
    try:
        _call_telegram_api('answerCallbackQuery', {
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': False,
        })
    except Exception:
        logger.exception('Failed to answer Telegram callback query')


def edit_review_message(chat_id, message_id, text):
    if not chat_id or not message_id:
        return
    try:
        _call_telegram_api('editMessageText', {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
        })
    except Exception:
        logger.exception('Failed to edit Telegram review message')
