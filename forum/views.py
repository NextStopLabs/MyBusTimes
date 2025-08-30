# Python standard library imports
import io
import json
import markdown
from concurrent.futures import thread
from datetime import timedelta, datetime, date

# Django imports
from django.db.models import Max
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseServerError, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.http import JsonResponse
from django.core.serializers import serialize

# Third-party imports
from PIL import Image
import requests

# Local/app imports
from .models import Thread, Post, Forum
from .forms import ThreadForm, PostForm
from main.models import CustomUser

def forum_banned(request):
    return render(request, 'forum_banned.html')

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

@csrf_exempt
def check_thread(request, discord_channel_id):
    exists = Thread.objects.filter(discord_channel_id=str(discord_channel_id)).exists()
    if exists:
        return JsonResponse({"exists": True})
    return JsonResponse({"exists": False}, status=404)

@csrf_exempt
@require_POST
def create_thread_from_discord(request):
    data = json.loads(request.body)

    title = data.get("title")
    discord_channel_id = data.get("discord_channel_id")
    forum_id = data.get("forum_id")  # ✅ new
    created_by = data.get("created_by")
    first_post = data.get("first_post", "")

    if not (title and discord_channel_id and created_by and forum_id):
        return JsonResponse({"error": "Missing data"}, status=400)
    
    print(f"[DEBUG] Creating thread: title={title}, discord_channel_id={discord_channel_id}, forum_id={forum_id}, created_by={created_by}")

    thread = Thread.objects.create(
        title=title,
        created_by=created_by,  # ✅ use value from the request
        discord_channel_id=discord_channel_id,
        forum=Forum.objects.filter(discord_forum_id=forum_id).first(),  # ✅ store forum ID
    )

    Post.objects.create(
        thread=thread,
        author=created_by,
        content=first_post
    )

    return JsonResponse({"status": "created", "thread_id": thread.id})

def forum_list(request):
    if request.user.is_authenticated and request.user.forum_banned:
        return redirect('forum_banned')

    # Annotate threads with latest post date
    forum_list = Forum.objects.all().order_by('order', 'name')

    return render(request, 'forum_list.html', {
        'forums': forum_list,
    })


def thread_list(request, forum_name):
    if request.user.is_authenticated and request.user.forum_banned:
        return redirect('forum_banned')
    # Annotate threads with latest post date
    threads_with_latest_post = Thread.objects.filter(forum__name=forum_name).annotate(
        latest_post=Max('posts__created_at')
    ).order_by('-pinned', '-latest_post', '-created_at')

    # Separate pinned vs unpinned threads
    pinned_threads = threads_with_latest_post.filter(pinned=True)

    unpinned_threads = threads_with_latest_post.filter(pinned=False)

    # Group unpinned threads by forum
    forums = Forum.objects.all().order_by('order', 'name')
    forum_threads = []
    for forum in forums:
        threads = unpinned_threads.filter(forum=forum)
        if threads.exists():
            forum_threads.append({
                'forum': forum,
                'threads': threads
            })

    return render(request, 'thread_list.html', {
        'pinned_threads': pinned_threads,
        'forum_threads': forum_threads,
        'forum_name': forum_name,
    })

def thread_details_api(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    all_posts = thread.posts.order_by('created_at')

    paginator = Paginator(all_posts, 100)  # 100 posts per page
    page_number = request.GET.get('page')

    if page_number is None:
        # Redirect to the last page
        last_page_number = paginator.num_pages
        return redirect(f'/api/thread/{thread.id}/?page={last_page_number}')

    page_obj = paginator.get_page(page_number)

    posts_with_pfps = []
    for post in page_obj:
        user = CustomUser.objects.filter(
            Q(username=post.author) | Q(discord_username=post.author)
        ).first()
        pfp = user.pfp.url if user and user.pfp else None

        online = False
        if user and user.last_active and user.last_active > timezone.now() - timedelta(minutes=5):
            online = True

        if user and user.discord_username == post.author:
            author = f"{user.username} | {post.author} (Discord)"
            username = user.username
        else:
            author = post.author
            username = post.author

        if user and user.badges:
            user_badges = user.badges.all()
            user_badges = serialize("json", user_badges)
            user_badges = json.loads(user_badges)
        else:
            user_badges = []

        unformated_html_post = post.content
        formated_html_post = markdown.markdown(unformated_html_post)

        if post.image:
            image = post.image.url
        else:
            image = ""

        posts_with_pfps.append({
            'post': {
                "id": post.id,
                "content": post.content,
                "created_at": post.created_at.isoformat(),  # datetime → string
                "formated_date": post.created_at.strftime('%H:%M %Y/%m/%d'),
                "html": formated_html_post,
                "image": image
            },
            'pfp': pfp,
            'user': {
                "id": user.id if user else None,
                "username": user.username if user else None,
                "discord_username": user.discord_username if user else None,
                "badges": user_badges,
            } if user else None,
            'online': online,
            'author': author,
            'username': username,
            'from_discord': bool(user and user.discord_username == post.author),
        })

        latest_message = post.created_at

    return JsonResponse({
        'status': 'success',
        'thread_id': thread.id,
        'latest_message_time': latest_message,
        'posts': posts_with_pfps
    })

def thread_detail(request, thread_id):
    if request.user.is_authenticated and request.user.forum_banned:
        return redirect('forum_banned')
    
    thread = get_object_or_404(Thread, pk=thread_id)
    all_posts = thread.posts.order_by('created_at')

    paginator = Paginator(all_posts, 100)  # 100 posts per page
    page_number = request.GET.get('page')

    if page_number is None:
        # Redirect to the last page
        last_page_number = paginator.num_pages
        return redirect(f'/forum/thread/{thread.id}/?page={last_page_number}')

    page_obj = paginator.get_page(page_number)

    posts_with_pfps = []
    for post in page_obj:
        user = CustomUser.objects.filter(
            Q(username=post.author) | Q(discord_username=post.author)
        ).first()
        pfp = user.pfp.url if user and user.pfp else None

        online = False
        if user and user.last_active and user.last_active > timezone.now() - timedelta(minutes=5):
            online = True

        if user and user.discord_username == post.author:
            author = f"{user.username} | {post.author} (Discord)"
        else:
            author = post.author

        posts_with_pfps.append({
            'post': post,
            'pfp': pfp,
            'user_obj': user,
            'online': online,
            'author': author,
            'from_discord': user and user.discord_username == post.author
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
                        if img.mode == "P":
                            img = img.convert("RGB")

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

            # After post.save()
            post_count = thread.posts.filter(created_at__lte=post.created_at).count()
            posts_per_page = paginator.per_page
            page_number = (post_count - 1) // posts_per_page + 1

            thread_url = reverse('thread_detail', args=[thread.id])
            return redirect(f"{thread_url}?page={page_number}#post-{post.id}")
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
    if request.user.is_authenticated and request.user.forum_banned:
        return redirect('forum_banned')
    
    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.created_by = request.user.username
            thread.save()

            # Create first post
            Post.objects.create(
                thread=thread,
                author=request.user.username,
                content=form.cleaned_data['content']
            )

            # 🔁 Call the Discord Bot API to create a new thread
            try:
                response = requests.post(f"{settings.DISCORD_BOT_API_URL}/create-thread", json={
                    'title': thread.title,
                    'content': form.cleaned_data['content']
                })
                response.raise_for_status()

                thread_id = response.json().get('thread_id')
                if thread_id:
                    thread.discord_channel_id = thread_id
                    thread.save(update_fields=['discord_channel_id'])

            except requests.RequestException as e:
                print(f"[Discord API Error] {e}")
                return HttpResponseServerError("Failed to communicate with Discord API.")

            return redirect('thread_detail', thread_id=thread.id)
    else:
        form = ThreadForm()

    return render(request, 'new_thread.html', {'form': form})