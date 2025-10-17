import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message, Chat, ChatMember, ReadReceipt

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'
        user = self.scope['user']

        print(f"[CONNECT] User {user} connecting to chat {self.chat_id}")

        if not user.is_authenticated:
            print("[CONNECT] User not authenticated, closing connection")
            await self.close()
            return

        is_member = await self.is_member(user.id)
        print(f"[CONNECT] Is user member of chat? {is_member}")

        if not is_member:
            print(f"[CONNECT] User {user} is NOT a member of chat {self.chat_id}, closing connection")
            await self.close()
            return

        await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
        await self.accept()
        print("[CONNECT] Connection accepted")

        await self.update_last_seen(user.id)
        print("[CONNECT] Updated last seen timestamp")

    async def disconnect(self, close_code):
        print(f"[DISCONNECT] Disconnecting from chat group {self.chat_group_name}")
        await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)

    async def receive(self, text_data):
        print(f"[RECEIVE] Raw data: {text_data}")
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as e:
            print(f"[RECEIVE] JSON decode error: {e}")
            return

        user = self.scope['user']
        message_text = data.get('message', '').strip()
        image_url = data.get('image')  # frontend should send this if uploading image
        file_url = data.get('file')    # frontend should send this if uploading file

        if not any([message_text, image_url, file_url]):
            print("[RECEIVE] Empty message received, ignoring")
            return

        try:
            msg = await self.create_message(user.id, message_text, image_url, file_url)
            print(f"[RECEIVE] Saved message {msg.id} to DB")
        except Exception as e:
            print(f"[RECEIVE] Error saving message: {e}")
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
        print("[RECEIVE] Broadcasted message to group")

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
        print(f"[DB] is_member check for user_id={user_id} and chat_id={self.chat_id}: {result}")
        return result

    @database_sync_to_async
    def update_last_seen(self, user_id):
        print(f"[DB] Updating last_seen_at for user_id={user_id} in chat_id={self.chat_id}")
        return ChatMember.objects.filter(chat_id=self.chat_id, user_id=user_id).update(last_seen_at=timezone.now())

    @database_sync_to_async
    def create_message(self, user_id, text, image=None, file=None):
        print(f"[DB] Creating message in chat_id={self.chat_id} from user_id={user_id}")
        chat = Chat.objects.get(id=self.chat_id)
        msg = Message.objects.create(
            chat=chat,
            sender_id=user_id,
            text=text,
            image=image if image else None,
            file=file if file else None
        )
        print(f"[DB] Created message id={msg.id}")
        return msg

    @database_sync_to_async
    def mark_as_read(self, user_id, message_id):
        print(f"[DB] Marking message id={message_id} as read by user_id={user_id}")
        return ReadReceipt.objects.get_or_create(message_id=message_id, user_id=user_id)
