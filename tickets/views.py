from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django import forms
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from .models import Ticket, TicketMessage, TicketType
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from main.models import UserKeys
import requests
import json

class TicketForm(forms.ModelForm):
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe your issue...'}),
        required=True,
        label="Message"
    )

    class Meta:
        model = Ticket
        fields = ['ticket_type']  # Remove 'priority'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ticket_type'].queryset = TicketType.objects.filter(active=True)

class TicketMessageForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ['content', 'files']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Type your message...'})
        }

@csrf_exempt
def ticket_list_api(request):
    if request.method == "GET":
        discord_channel_id = request.GET.get("discord_channel_id")

        if discord_channel_id:
            ticket = Ticket.objects.filter(discord_channel_id=discord_channel_id).first()
            if ticket:
                data = {
                    "id": ticket.id,
                    "status": ticket.get_status_display(),
                    "priority": ticket.get_priority_display()
                }
                return JsonResponse(data)
            else:
                return JsonResponse({"error": "Ticket not found"}, status=404)
    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def ticket_home(request):
    mytickets = Ticket.objects.filter(user=request.user).order_by('-created_at')

    if request.user.is_superuser:
        myteamticketers = Ticket.objects.filter(status='open').order_by('-created_at')
    else:
        myteamticketers = Ticket.objects.filter(assigned_team=request.user.mbt_team, status='open').order_by('-created_at') if request.user.mbt_team else Ticket.objects.none()

    return render(request, "ticket_home.html", {"mytickets": mytickets, "myteamticketers": myteamticketers})

@login_required
def ticket_messages_api(request, ticket_id):
    assigned_teams = [request.user.mbt_team] if request.user.mbt_team else []

    if request.user.is_superuser:
        ticket = get_object_or_404(Ticket, id=ticket_id)
    else:
        ticket = get_object_or_404(
            Ticket.objects.filter(
                Q(user=request.user) |
                Q(assigned_team__in=assigned_teams) &
                Q(status='open')
            ),
        id=ticket_id
    )

    if request.method == "POST":
        content = request.POST.get("content")
        file = request.FILES.get("file")
        if content or file:
            ticket_message = TicketMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                content=content,
                files=file  # this saves the file to the model's storage
            )

            file_link = ""

            if ticket_message.files:
                file_link = f"https://www.mybustimes.cc{ticket_message.files.url}"

            data = {
                "channel_id": ticket.discord_channel_id,
                "send_by": request.user.username,
                "message": f"{content} \n\n {file_link}",
            }

            files = {}
            response = requests.post("http://localhost:8080/send-message", data=data, files=files)

            return JsonResponse({"status": "ok", "discord_status": response.status_code})
        return JsonResponse({"status": "ok"})

    messages = ticket.messages.all().order_by("created_at")
    data = {
        "info": [
            {
                "id": ticket.id,
                "status": ticket.get_status_display(),
                "priority": ticket.get_priority_display()
            }
        ],
        "messages": [
            {
                "sender": username if (username := msg.username) else str(msg.sender),
                "content": msg.content,
                "files": msg.files.url if msg.files else None,
                "created_at": timezone.localtime(msg.created_at).strftime("%H:%M")  # convert to local timezone
            } for msg in messages
        ]
    }
    return JsonResponse(data)

@csrf_exempt
def ticket_messages_api_key_auth(request, ticket_id):
    key = request.headers.get("Authorization")
    if not key:
        return JsonResponse({"error": "Missing Authorization header"}, status=401)

    user_key = UserKeys.objects.filter(session_key=key).first()
    user = user_key.user if user_key else None

    if not user:
        return JsonResponse({"error": "Invalid API key"}, status=403)

    assigned_teams = [user.mbt_team] if user.mbt_team else []

    if user.is_superuser:
        ticket = get_object_or_404(Ticket, id=ticket_id)
    else:
        ticket = get_object_or_404(
            Ticket.objects.filter(
                (Q(user=user) | Q(assigned_team__in=assigned_teams)) &
                Q(status='open')
            ),
            id=ticket_id
        )

    if request.method == "POST":
        content = None
        sender_username = user.username  # default
        file = None

        if request.content_type == "application/json":
            try:
                body = json.loads(request.body)
                content = body.get("content")
                sender_username = body.get("sender_username")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)
        else:
            content = request.POST.get("content")
            file = request.FILES.get("files")

        if not content and not file:
            return JsonResponse({"error": "No content or file provided"}, status=400)

        TicketMessage.objects.create(
            ticket=ticket,
            sender=user,
            username=sender_username,
            content=content,
            files=file
        )

        return JsonResponse({"status": "ok"})

    return JsonResponse({"error": "Invalid method"}, status=405)


@login_required
def close_ticket(request, ticket_id):
    # Ensure assigned_team is iterable
    assigned_teams = [request.user.mbt_team] if request.user.mbt_team else []

    if request.user.is_superuser:
        ticket = get_object_or_404(Ticket, id=ticket_id)
    else:
        ticket = get_object_or_404(
            Ticket.objects.filter(assigned_team__in=assigned_teams),
            id=ticket_id
        )

    if request.method == "POST":
        ticket.status = 'closed'
        ticket.save()

        response = requests.post("http://localhost:8080/delete-channel", json={"channel_id": ticket.discord_channel_id})
        if response.status_code == 200:
            return redirect("ticket_detail", ticket_id=ticket.id)

@login_required
def ticket_detail(request, ticket_id):
    # Ensure assigned_team is iterable
    assigned_teams = [request.user.mbt_team] if request.user.mbt_team else []

    if request.method == "POST":
        priority = request.POST.get("priority")
        if priority:
            ticket = get_object_or_404(Ticket, id=ticket_id)
            ticket.priority = priority
            ticket.save()

    if request.user.is_superuser:
        ticket = get_object_or_404(Ticket, id=ticket_id)

    else:
        ticket = get_object_or_404(
            Ticket.objects.filter(
                Q(user=request.user) |
                Q(assigned_team__in=assigned_teams)
            ),
        id=ticket_id
    )

    if request.user.mbt_team == ticket.assigned_team or request.user.is_superuser:
        is_admin = True
    else:
        is_admin = False

    return render(request, "ticket_detail.html", {"ticket": ticket, "is_admin": is_admin, "is_closed": ticket.status == 'closed'})

@login_required
def create_ticket(request):
    if request.method == "POST":
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.assigned_team = ticket.ticket_type.team
            ticket.priority = "medium"  # <- Set default here
            ticket.save()

            # Create first message
            TicketMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                content=form.cleaned_data['message']
            )

            data = {
                "channel_name": f"mbt-ticket-{ticket.id}",
                "category_id": ticket.ticket_type.discord_category_id,
            }

            response = requests.post("http://localhost:8080/create-channel", data=data)

            ticket.discord_channel_id = response.json().get("channel_id")
            ticket.save()

            data = {
                "channel_id": ticket.discord_channel_id,
                "send_by": request.user.username,
                "message": f"This ticket was opened on the website to close please go to https://www.mybustimes.cc/tickets/{ticket.id}/ \n\n {form.cleaned_data['message']}",
            }

            files = {}

            response = requests.post("http://localhost:8080/send-message", data=data, files=files)

            return redirect("ticket_detail", ticket_id=ticket.id)
        else:
            print(form.errors)  # debug invalid form
    else:
        form = TicketForm()

    return render(request, "create_ticket.html", {"form": form})

