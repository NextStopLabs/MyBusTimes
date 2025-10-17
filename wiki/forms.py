from markdownx.fields import MarkdownxFormField
from django import forms
from .models import WikiPage

class WikiPageForm(forms.ModelForm):
    content = MarkdownxFormField()

    class Meta:
        model = WikiPage
        fields = ['title', 'content', 'category', 'tags']
