from django import forms
from django.contrib.auth import get_user_model
from django_select2.forms import Select2MultipleWidget  # <-- Select2 widget

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
        widget=Select2MultipleWidget(attrs={"data-placeholder": "Search for users..."}),
        required=True,
        help_text="Select one or more users to chat with"
    )

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)
        if current_user:
            self.fields["users"].queryset = User.objects.exclude(pk=current_user.pk).order_by("username")
        else:
            self.fields["users"].queryset = User.objects.all().order_by("username")
