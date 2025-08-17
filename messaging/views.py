from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import StartChatForm
from .models import Chat, ChatMember, Message
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Prefetch
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@login_required
def send_file(request):
    if request.method == "POST":
        chat_id = request.POST.get("chat_id")
        text = request.POST.get("text", "")
        uploaded_file = request.FILES.get("file")

        chat = Chat.objects.get(id=chat_id)

        image_file = None
        file_field = None

        if uploaded_file:
            if uploaded_file.content_type.startswith("image/"):
                # Open image with Pillow
                img = Image.open(uploaded_file)
                
                # Convert to RGB if necessary (some formats like PNG have alpha)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Resize if too large (optional, e.g., max 1080px)
                max_size = (1080, 1080)
                img.thumbnail(max_size, Image.ANTIALIAS)

                # Save compressed image to memory
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=70)  # adjust quality 70-85
                buffer.seek(0)

                # Create Django file object
                image_file = ContentFile(buffer.read(), name=uploaded_file.name.rsplit('.', 1)[0] + ".jpg")
            else:
                file_field = uploaded_file

        message = Message.objects.create(
            chat=chat,
            sender=request.user,
            text=text or "",
            image=image_file,
            file=file_field
        )

        # Broadcast via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat_id}",
            {
                "type": "chat_message",
                "message": message.text,
                "sender": request.user.username,
                "timestamp": message.created_at.strftime("%Y-%m-%d %H:%M"),
                "image_url": message.image.url if message.image else None,
                "file_url": message.file.url if message.file else None,
            }
        )

        return JsonResponse({"status": "ok", "message_id": message.id})

    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def home(request):
    user = request.user

    # Prefetch only the most recent message for each chat
    last_message_qs = Message.objects.filter(is_deleted=False).order_by("-created_at")

    chats = (
        user.chats.all()
        .prefetch_related("members", Prefetch("messages", queryset=last_message_qs, to_attr="prefetched_messages"))
        .order_by("-created_at")
    )

    for chat in chats:
        # Direct chat - store other user for template
        if chat.chat_type == "direct":
            other_members = [m for m in chat.members.all() if m.id != user.id]
            chat.other_user = other_members[0] if other_members else None
        else:
            chat.other_user = None

        # Store last message for template
        chat.last_message = chat.prefetched_messages[0] if chat.prefetched_messages else None

    return render(request, "msghome.html", {"chats": chats})

@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    ChatMember.objects.filter(chat=chat, user=request.user).update(last_seen_at=timezone.now())
    messages = chat.messages.filter(is_deleted=False).order_by("created_at")[:50]
    return render(request, "chat_detail.html", {
        "chat": chat,
        "messages": messages,
    })

@login_required
def start_chat(request):
    if request.method == "POST":
        form = StartChatForm(request.POST, current_user=request.user)
        if form.is_valid():
            chat_type = form.cleaned_data["chat_type"]
            name = form.cleaned_data["name"].strip()
            selected_users = form.cleaned_data["users"]

            if chat_type == "direct":
                # For direct chats, make sure only one user is selected
                if selected_users.count() != 1:
                    form.add_error("users", "Please select exactly one user for a direct message.")
                else:
                    # Check if a direct chat already exists between these two users
                    user_ids = sorted([request.user.id, selected_users.first().id])
                    existing_chats = Chat.objects.filter(
                        chat_type="direct",
                        members__id=user_ids[0]
                    ).filter(
                        members__id=user_ids[1]
                    ).distinct()

                    # A direct chat between two users should have exactly 2 members
                    existing_chats = [c for c in existing_chats if c.members.count() == 2]

                    if existing_chats:
                        return redirect("chat_detail", chat_id=existing_chats[0].id)

                    # Create new direct chat
                    chat = Chat.objects.create(chat_type="direct", created_by=request.user)
                    ChatMember.objects.create(chat=chat, user=request.user, is_admin=True)
                    ChatMember.objects.create(chat=chat, user=selected_users.first())
                    return redirect("chat_detail", chat_id=chat.id)

            else:
                # For group chats, name is required
                if not name:
                    form.add_error("name", "Group chat name is required.")
                else:
                    chat = Chat.objects.create(chat_type=chat_type, name=name, created_by=request.user)
                    ChatMember.objects.create(chat=chat, user=request.user, is_admin=True)
                    for user in selected_users:
                        ChatMember.objects.create(chat=chat, user=user)
                    return redirect("chat_detail", chat_id=chat.id)

    else:
        form = StartChatForm(current_user=request.user)

    return render(request, "start_chat.html", {"form": form})