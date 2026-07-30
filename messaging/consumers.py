import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message, Chat, ChatMember, ReadReceipt
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'
        user = self.scope['user']

        if not user.is_authenticated:
            await self.close()
            return

        is_member = await self.is_member(user.id)
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
        await self.accept()

        await self.update_last_seen(user.id)
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as e:
            return

        user = self.scope['user']
        message_text = data.get('message', '').strip()
        image_url = data.get('image')  # frontend should send this if uploading image
        file_url = data.get('file')    # frontend should send this if uploading file

        if not any([message_text, image_url, file_url]):
            return

        try:
            msg = await self.create_message(user.id, message_text, image_url, file_url)
        except Exception as e:
            return

        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message': msg.text,
                'image': msg.image.url if msg.image else None,
                'file': msg.file.url if msg.file else None,
                'sender': user.username,
                'timestamp': msg.created_at.strftime('%Y-%m-%d %H:%M'),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event.get('message'),
            'sender': event.get('sender'),
            'timestamp': event.get('timestamp'),
            'image_url': event.get('image_url'),
            'file_url': event.get('file_url'),
        }))

    @database_sync_to_async
    def is_member(self, user_id):
        result = ChatMember.objects.filter(chat_id=self.chat_id, user_id=user_id).exists()
        return result

    @database_sync_to_async
    def update_last_seen(self, user_id):
        return ChatMember.objects.filter(chat_id=self.chat_id, user_id=user_id).update(last_seen_at=timezone.now())

    @database_sync_to_async
    def create_message(self, user_id, text, image=None, file=None):
        try:
            chat = Chat.objects.get(id=self.chat_id)
        except Chat.DoesNotExist:
            logger.warning("Chat %s no longer exists for new message", self.chat_id)
            return None
        msg = Message.objects.create(
            chat=chat,
            sender_id=user_id,
            text=text,
            image=image if image else None,
            file=file if file else None
        )
        return msg

    @database_sync_to_async
    def mark_as_read(self, user_id, message_id):
        return ReadReceipt.objects.get_or_create(message_id=message_id, user_id=user_id)
