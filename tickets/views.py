from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django import forms
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from .models import Ticket, TicketMessage, TicketType
from django.db.models import Q

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

@login_required
def ticket_home(request):
    mytickets = Ticket.objects.filter(user=request.user).order_by('-created_at')

    if request.user.is_superuser:
        myteamticketers = Ticket.objects.all().order_by('-created_at')
    else:
        myteamticketers = Ticket.objects.filter(assigned_team=request.user.mbt_team).order_by('-created_at') if request.user.mbt_team else Ticket.objects.none()

    return render(request, "ticket_home.html", {"mytickets": mytickets, "myteamticketers": myteamticketers})

@login_required
def ticket_messages_api(request, ticket_id):
    assigned_teams = [request.user.mbt_team] if request.user.mbt_team else []

    ticket = get_object_or_404(
        Ticket.objects.filter(
            Q(user=request.user) |
            Q(assigned_team__in=assigned_teams)
        ),
        id=ticket_id
    )

    if request.method == "POST":
        content = request.POST.get("content")
        file = request.FILES.get("file")
        if content or file:
            TicketMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                content=content,
                files=file
            )
        return JsonResponse({"status": "ok"})

    messages = ticket.messages.all().order_by("created_at")
    data = {
        "messages": [
            {
                "sender": msg.sender.username,
                "content": msg.content,
                "files": msg.files.url if msg.files else None,
                "created_at": timezone.localtime(msg.created_at).strftime("%H:%M")  # convert to local timezone
            } for msg in messages
        ]
    }
    return JsonResponse(data)

@login_required
def ticket_detail(request, ticket_id):
    # Ensure assigned_team is iterable
    assigned_teams = [request.user.mbt_team] if request.user.mbt_team else []

    ticket = get_object_or_404(
        Ticket.objects.filter(
            Q(user=request.user) |
            Q(assigned_team__in=assigned_teams)
        ),
        id=ticket_id
    )

    return render(request, "ticket_detail.html", {"ticket": ticket})

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

            return redirect("ticket_detail", ticket_id=ticket.id)
        else:
            print(form.errors)  # debug invalid form
    else:
        form = TicketForm()

    return render(request, "create_ticket.html", {"form": form})

