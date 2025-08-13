from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import StartChatForm
from .models import Chat, ChatMember
from django.shortcuts import get_object_or_404
from django.utils import timezone

@login_required
def home(request):
    user = request.user
    # Get chats where the user is a member
    chats = user.chats.all().order_by("-created_at")  # Chats user belongs to, newest first
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