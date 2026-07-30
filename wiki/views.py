from .models import WikiPage, WikiPageVersion
from main.models import badge
from django.db.models import Q, F
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import WikiPageForm
from django.contrib.admin.views.decorators import staff_member_required
import markdown
import bleach
import logging
from django.utils.safestring import mark_safe
from django.utils.html import escape

logger = logging.getLogger(__name__)

_MD_EXTENSIONS = ['fenced_code', 'codehilite', 'tables']

# n3-based allowlist (already a project dependency used elsewhere)
_ALLOWED_TAGS = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
    'a', 'img', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'strong', 'em',
    'del', 'span', 'div'
]
_ALLOWED_ATTRS = {
    'a': ['href', 'title', 'rel', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'span': ['class'],
    'code': ['class'],
    'div': ['class'],
}


def render_markdown(content):
    """Render user-authored markdown to sanitized HTML, never raising."""
    if not content:
        return mark_safe('')
    try:
        raw_html = markdown.markdown(content, extensions=_MD_EXTENSIONS)
        clean_html = bleach.clean(
            raw_html,
            tags=_ALLOWED_TAGS,
            attributes=_ALLOWED_ATTRS,
            strip=True,
        )
        return mark_safe(clean_html)
    except Exception:
        logger.exception("Failed to render wiki markdown")
        return mark_safe(escape(content))

def wiki_edit_banned(request):
    return render(request, 'wiki_edit_banned.html')

@staff_member_required
def pending_pages(request):
    # New/unapproved pages
    unapproved_pages = WikiPage.objects.filter(is_approved=False)

    # Approved pages with pending versions
    edited_pages = WikiPage.objects.filter(is_approved=True).filter(
        versions__created_at__gt=F('updated_at')
    ).distinct()

    # Combine both querysets
    pending = list(unapproved_pages) + list(edited_pages)

    return render(request, 'pending_pages.html', {'pending_pages': pending})


@staff_member_required
def approve_page(request, slug):
    page = get_object_or_404(WikiPage, slug=slug)
    latest_version = page.latest_version()

    if latest_version:
        # Check if editor of latest_version has the "Wiki Contributor" badge
        contributor_badge = badge.objects.filter(badge_name="Wiki Contributor").first()
        editor = latest_version.edited_by
        if contributor_badge and editor and not editor.badges.filter(id=contributor_badge.id).exists():
            editor.badges.add(contributor_badge)
            editor.save()

        # Save current page to version history
        WikiPageVersion.objects.create(
            page=page,
            content=page.content,
            edited_by=page.author,  # this can stay the same if you want
            edit_summary='Auto-saved before approval'
        )
        # Promote version content to page
        page.content = latest_version.content
        page.updated_at = latest_version.created_at
        page.is_approved = True
        page.save()
        # Delete draft version
        latest_version.delete()

    return redirect('pending_pages')

@login_required
def create_wiki_page(request):
    if request.user.is_authenticated and request.user.banned_from.filter(name='wiki_edit').exists():
        return redirect('wiki_edit_banned')
    if request.method == 'POST':
        form = WikiPageForm(request.POST)
        if form.is_valid():
            wiki_page = form.save(commit=False)
            wiki_page.author = request.user
            wiki_page.is_approved = False  # Mark as pending
            wiki_page.save()
            form.save_m2m()
            return render(request, 'submit_success.html')
    else:
        form = WikiPageForm()
    return render(request, 'create_page.html', {'form': form})

@login_required
def edit_wiki_page(request, slug):
    if request.user.is_authenticated and request.user.banned_from.filter(name='wiki_edit').exists():
        return redirect('wiki_edit_banned')
    page = get_object_or_404(WikiPage, slug=slug)

    if request.method == 'POST':
        form = WikiPageForm(request.POST, instance=page)
        if form.is_valid():
            # Save to version instead of modifying main page
            version = WikiPageVersion.objects.create(
                page=page,
                content=form.cleaned_data['content'],
                edited_by=request.user,
                edit_summary='Pending edit submitted.'
            )
            return render(request, 'submit_success.html')
    else:
        form = WikiPageForm(instance=page)

    return render(request, 'edit_page.html', {'form': form, 'page': page})

def wiki_home(request):
    query = request.GET.get('q', '')

    if query:
        pages = WikiPage.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query),
            is_approved=True
        ).order_by('title')
    else:
        pages = WikiPage.objects.filter(is_approved=True).order_by('title')

    context = {
        'pages': pages,
        'query': query,
    }
    return render(request, 'home.html', context)

def wiki_detail(request, slug):
    page = get_object_or_404(WikiPage, slug=slug, is_approved=True)
    content_html = render_markdown(page.content)
    return render(request, 'detail.html', {'page': page, 'content_html': content_html})

@staff_member_required
def pending_page(request, slug):
    page = get_object_or_404(WikiPage, slug=slug)

    # Get latest pending version (if any)
    latest_version = page.latest_version()

    if latest_version:
        # Render markdown from the pending draft version content
        content_html = render_markdown(latest_version.content)
        content_source = "Pending Draft"
    else:
        # No pending version, fallback to current page content
        content_html = render_markdown(page.content)
        content_source = "Current Approved"

    return render(request, 'detail.html', {
        'page': page,
        'content_html': content_html,
        'content_source': content_source,  # Optional: indicate which content is shown
    })