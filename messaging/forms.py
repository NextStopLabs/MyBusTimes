from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class StartChatForm(forms.Form):
    chat_type = forms.ChoiceField(
        choices=[("direct", "Direct Message"), ("group_private", "Group")],
        widget=forms.RadioSelect,
        initial="direct"
    )
    name = forms.CharField(required=False, max_length=255, help_text="Required for group chats")
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={"size": 10, "class": "form-control"}),
        required=True,
        help_text="Select one or more users to chat with"
    )

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)
        if current_user:
            # Exclude current user from user list
            self.fields["users"].queryset = User.objects.exclude(pk=current_user.pk).order_by("username")
        else:
            self.fields["users"].queryset = User.objects.all().order_by("username")
