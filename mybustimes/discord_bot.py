import discord
from django.conf import settings
import asyncio

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def send_for_sale_message(message_content: str):
    await client.wait_until_ready()
    channel = client.get_channel(int(settings.DISCORD_FOR_SALE_CHANNEL))
    if channel:
        await channel.send(message_content)

def run_bot():
    loop = asyncio.get_event_loop()
    loop.create_task(client.start(settings.DISCORD_BOT_TOKEN))
    # We don't block here, so call run_bot once at app start (maybe in apps.py ready())
