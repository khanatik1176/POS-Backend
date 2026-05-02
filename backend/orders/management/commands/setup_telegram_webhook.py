import json
import logging
from urllib import request

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set up or verify Telegram webhook configuration'

    def add_arguments(self, parser):
        parser.add_argument('--webhook-url', type=str, help='Webhook URL (e.g., https://mysite.com/api/telegram/webhook/)')
        parser.add_argument('--verify', action='store_true', help='Only verify current webhook, don\'t set a new one')
        parser.add_argument('--remove', action='store_true', help='Remove the webhook')

    def call_telegram_api(self, method, payload=None):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            raise CommandError('TELEGRAM_BOT_TOKEN not set in settings')

        url = f'https://api.telegram.org/bot{token}/{method}'
        req = request.Request(
            url,
            data=json.dumps(payload or {}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with request.urlopen(req, timeout=10) as response:
                body = response.read().decode('utf-8')
                return json.loads(body)
        except Exception as e:
            raise CommandError(f'Telegram API error: {e}')

    def handle(self, *args, **options):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            raise CommandError('❌ TELEGRAM_BOT_TOKEN is not set. Set it in your environment variables.')

        if options['verify']:
            self.verify_webhook()
        elif options['remove']:
            self.remove_webhook()
        elif options['webhook_url']:
            self.setup_webhook(options['webhook_url'])
        else:
            self.verify_webhook()

    def setup_webhook(self, webhook_url):
        """Register webhook with Telegram"""
        self.stdout.write(f'Setting up webhook: {webhook_url}')

        # First, verify the webhook URL is accessible
        try:
            req = request.Request(webhook_url, method='HEAD', headers={'User-Agent': 'TelegramBot'})
            with request.urlopen(req, timeout=5) as resp:
                if resp.status not in (200, 404, 405):  # 405 Method Not Allowed is OK (we're using HEAD)
                    self.stdout.write(self.style.WARNING(f'⚠️  Webhook URL returned {resp.status}. Make sure it\'s publicly accessible.'))
        except Exception as e:
            raise CommandError(f'❌ Cannot reach webhook URL: {e}. Ensure your URL is publicly accessible over HTTPS.')

        # Register with Telegram
        response = self.call_telegram_api('setWebhook', {
            'url': webhook_url,
            'secret_token': getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', ''),
            'allowed_updates': ['callback_query', 'message'],
        })

        if response.get('ok'):
            self.stdout.write(self.style.SUCCESS('✓ Webhook registered successfully!'))
            self.stdout.write(f'  URL: {webhook_url}')
            self.verify_webhook()
        else:
            raise CommandError(f'❌ Telegram API error: {response.get("description")}')

    def verify_webhook(self):
        """Check current webhook status"""
        self.stdout.write('Checking webhook info...')

        response = self.call_telegram_api('getWebhookInfo')
        if not response.get('ok'):
            raise CommandError(f'❌ Error: {response.get("description")}')

        info = response.get('result', {})
        url = info.get('url')
        pending_count = info.get('pending_update_count', 0)
        last_error_date = info.get('last_error_date')
        last_error_msg = info.get('last_error_message')

        if url:
            self.stdout.write(self.style.SUCCESS(f'✓ Webhook is set:'))
            self.stdout.write(f'  URL: {url}')
            self.stdout.write(f'  Pending updates: {pending_count}')
            if last_error_date:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Last error (timestamp {last_error_date}): {last_error_msg}'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  No webhook is currently set.'))

    def remove_webhook(self):
        """Remove webhook"""
        self.stdout.write('Removing webhook...')

        response = self.call_telegram_api('deleteWebhook')
        if response.get('ok'):
            self.stdout.write(self.style.SUCCESS('✓ Webhook removed.'))
        else:
            raise CommandError(f'❌ Error: {response.get("description")}')
