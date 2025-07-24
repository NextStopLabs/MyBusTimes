from concurrent.futures import thread
from django.shortcuts import render, get_object_or_404, redirect
from .models import Thread, Post
from django.contrib.auth.decorators import login_required
from .forms import ThreadForm, PostForm
import requests
from django.conf import settings
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from PIL import Image
import io
from django.http import HttpResponseServerError
from django.core.paginator import Paginator
from main.models import CustomUser

@csrf_exempt
@require_POST
def discord_message(request):
    # Accept JSON or multipart/form-data
    if request.content_type == "application/json":
        data = json.loads(request.body)
        thread_channel_id = data.get("thread_channel_id")
        author = data.get("author")
        content = data.get("content")
        image = None
    else:
        thread_channel_id = request.POST.get("thread_channel_id")
        author = request.POST.get("author")
        content = request.POST.get("content")
        image = request.FILES.get("image")

    try:
        thread = Thread.objects.get(discord_channel_id=str(thread_channel_id))
    except Thread.DoesNotExist:
        return JsonResponse({"error": "Thread not found"}, status=404)

    post = Post(thread=thread, author=author, content=content)
    if image:
        post.image = image
    post.save()

    return JsonResponse({"status": "success", "post_id": post.id})

def thread_list(request):
    threads = Thread.objects.all().order_by('-created_at')
    return render(request, 'thread_list.html', {'threads': threads})

def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    all_posts = thread.posts.order_by('created_at')

    paginator = Paginator(all_posts, 1)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    posts_with_pfps = []
    for post in page_obj:
        user = CustomUser.objects.filter(username=post.author).first()
        pfp = user.pfp.url if user and user.pfp else None
        posts_with_pfps.append({
            'post': post,
            'pfp': pfp,
            'user_obj': user,
        })

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.thread = thread
            post.author = request.user.username
            post.save()

            # Enforce message_limit
            max_messages = thread.message_limit
            current_count = thread.posts.count()
            if current_count > max_messages and max_messages > 0:
                # Calculate how many oldest posts to delete
                to_delete_count = current_count - max_messages
                # Get the oldest posts ordered by creation time (assumed field: created_at)
                oldest_post_ids = thread.posts.order_by('created_at').values_list('id', flat=True)[:to_delete_count]
                thread.posts.filter(id__in=list(oldest_post_ids)).delete()

            if thread.discord_channel_id:
                try:
                    data = {
                        'channel_id': str(thread.discord_channel_id),
                        'send_by': request.user.username,
                        'message': post.content,
                    }
                    files = {}

                    if post.image:
                        # Open the image
                        img = Image.open(post.image)

                        if img.mode == 'RGBA':
                            img = img.convert('RGB')

                        # Resize or compress image here
                        # Example: resize image to max width/height of 1024px
                        max_size = (1024, 1024)
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)

                        # Save to BytesIO as JPEG with quality compression
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='JPEG', quality=85)
                        img_byte_arr.seek(0)

                        # Check size and further reduce quality if needed
                        while img_byte_arr.getbuffer().nbytes > 10 * 1024 * 1024:  # 10MB
                            img_byte_arr.truncate(0)
                            img_byte_arr.seek(0)
                            quality = max(10, int(img.info.get('quality', 85) * 0.8))
                            img.save(img_byte_arr, format='JPEG', quality=quality)
                            img_byte_arr.seek(0)
                            if quality == 10:
                                break

                        files['image'] = (post.image.name, img_byte_arr, 'image/jpeg')

                    response = requests.post(
                        f"{settings.DISCORD_BOT_API_URL}/send-message",
                        data=data,
                        files=files if files else None
                    )
                    response.raise_for_status()
                except requests.RequestException as e:
                    print(f"[Discord API Error] Failed to send post: {e}")

            return redirect('thread_detail', thread_id=thread.id)
    else:
        form = PostForm()

    form = PostForm()

    return render(request, 'thread_detail.html', {
        'thread': thread,
        'posts': posts_with_pfps,  # Just the decorated posts
        'form': form,
        'page_obj': page_obj,      # Keep the real Page object
    })

@login_required
def new_thread(request):
    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.created_by = request.user
            thread.save()

            # Create first post
            Post.objects.create(
                thread=thread,
                author=request.user.username,
                content=form.cleaned_data['content']
            )

            # 🔁 Call the Discord Bot API to create a new channel
            try:
                response = requests.post(f"{settings.DISCORD_BOT_API_URL}/create-channel", json={
                    'title': thread.title
                })
                response.raise_for_status()

                channel_id = response.json().get('channel_id')
                if channel_id:
                    thread.discord_channel_id = channel_id
                    thread.save(update_fields=['discord_channel_id'])

                    # Optionally send a first message
                    data = {
                        'channel_id': channel_id,
                        'send_by': request.user.username,
                        'message': form.cleaned_data['content']
                    }
                    files = {}

                    response = requests.post(
                        f"{settings.DISCORD_BOT_API_URL}/send-message",
                        data=data,
                        files=files
                    )
                    response.raise_for_status()

            except requests.RequestException as e:
                print(f"[Discord API Error] {e}")
                return HttpResponseServerError("Failed to communicate with Discord API.")

            return redirect('thread_detail', thread_id=thread.id)
    else:
        form = ThreadForm()

    return render(request, 'new_thread.html', {'form': form})