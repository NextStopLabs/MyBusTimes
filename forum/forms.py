from django import forms
from .models import Thread, Post, Forum

class ThreadForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea, label='Post content')
    forum = forms.ModelChoiceField(
        queryset=Forum.objects.all().order_by('order', 'name'),
        label="Category",
        empty_label="Select a forum",
        required=True
    )

    class Meta:
        model = Thread
        fields = ['title', 'forum', 'content']  # Add 'forum' here

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image']
