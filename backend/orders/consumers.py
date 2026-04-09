import json
from channels.generic.websocket import AsyncWebsocketConsumer


class OrderUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        token = self.scope.get('query_string', b'').decode('utf-8')
        await self.channel_layer.group_add('orders', self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({'type': 'connected', 'query': token}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('orders', self.channel_name)

    async def order_event(self, event):
        await self.send(text_data=json.dumps(event.get('data', {})))
