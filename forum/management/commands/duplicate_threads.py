import io
from django.core.management.base import BaseCommand
from forum.models import Thread, Post
from django.conf import settings
from PIL import Image
import requests

class Command(BaseCommand):
    help = "Resync all threads by creating new Discord threads and resending posts"

    def add_arguments(self, parser):
        parser.add_argument(
            '--exclude',
            nargs='*',
            type=int,
            default=[],
            help='List of thread IDs to exclude from resync',
        )

    def handle(self, *args, **options):
        exclude_ids = options['exclude']
        self.stdout.write(f"Excluding threads with IDs: {exclude_ids}")

        threads = Thread.objects.exclude(id__in=exclude_ids)
        total = threads.count()
        self.stdout.write(f"Resyncing {total} threads...")

        for idx, old_thread in enumerate(threads, start=1):
            self.stdout.write(f"[{idx}/{total}] Processing thread ID {old_thread.id}: '{old_thread.title}'")

            # Create new thread on Discord
            try:
                response = requests.post(
                    f"{settings.DISCORD_BOT_API_URL}/create-thread",
                    json={'title': old_thread.title, 'content': f"Original thread created by {old_thread.created_by} at {old_thread.created_at}"}
                )
                response.raise_for_status()
            except requests.RequestException as e:
                self.stderr.write(f"Failed to create Discord thread for thread ID {old_thread.id}: {e}")
                continue

            discord_thread_id = response.json().get('thread_id')
            if not discord_thread_id:
                self.stderr.write(f"No thread_id returned from Discord API for thread ID {old_thread.id}")
                continue

            self.stdout.write(f"Created new Discord thread with ID {discord_thread_id}")

            # Resend all posts
            posts = old_thread.posts.order_by('created_at')
            for post in posts:
                files = {}
                # Handle image if exists
                if post.image:
                    try:
                        img = Image.open(post.image)
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')

                        max_size = (1024, 1024)
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)

                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='JPEG', quality=85)
                        img_byte_arr.seek(0)

                        # Compress if > 10MB
                        while img_byte_arr.getbuffer().nbytes > 10 * 1024 * 1024:
                            img_byte_arr.truncate(0)
                            img_byte_arr.seek(0)
                            img.save(img_byte_arr, format='JPEG', quality=50)
                            img_byte_arr.seek(0)

                        files['image'] = (post.image.name, img_byte_arr, 'image/jpeg')
                    except Exception as e:
                        self.stderr.write(f"Failed processing image for post ID {post.id}: {e}")

                content = post.content.strip() if post.content else ""

                # Skip posts with no content and no image
                if not content and not files:
                    self.stdout.write(f"Skipping post ID {post.id} with no content or image")
                    continue

                try:
                    payload = {
                        'channel_id': int(discord_thread_id),  # Use correct key and type (int)
                        'send_by': post.author,
                        'message': content,
                    }

                    r = requests.post(
                        f"{settings.DISCORD_BOT_API_URL}/send-message",
                        data=payload,
                        files=files if files else None
                    )
                    r.raise_for_status()
                except requests.RequestException as e:
                    err_resp = ''
                    if e.response is not None:
                        err_resp = e.response.text
                    self.stderr.write(f"Failed to resend post ID {post.id} in new Discord thread: {e} - Response: {err_resp}")

            # Update local thread with new discord_channel_id
            old_thread.discord_channel_id = str(discord_thread_id)
            old_thread.save(update_fields=['discord_channel_id'])
            self.stdout.write(self.style.SUCCESS(f"Thread ID {old_thread.id} resynced with Discord thread ID {discord_thread_id}"))

        self.stdout.write(self.style.SUCCESS("All threads resynced."))
