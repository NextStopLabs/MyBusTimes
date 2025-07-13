from django.shortcuts import render, get_object_or_404, redirect
from .models import Thread, Post
from django.contrib.auth.decorators import login_required
from .forms import ThreadForm, PostForm

def thread_list(request):
    threads = Thread.objects.all().order_by('-created_at')
    return render(request, 'thread_list.html', {'threads': threads})

def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    posts = thread.posts.all()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.thread = thread
            post.author = request.user
            post.save()
            return redirect('thread_detail', thread_id=thread.id)
    else:
        form = PostForm()

    return render(request, 'thread_detail.html', {
        'thread': thread,
        'posts': posts,
        'form': form
    })

@login_required
def new_thread(request):
    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.created_by = request.user
            thread.save()
            Post.objects.create(
                thread=thread,
                author=request.user,
                content=form.cleaned_data['content']
            )
            return redirect('thread_detail', thread_id=thread.id)
    else:
        form = ThreadForm()
    return render(request, 'new_thread.html', {'form': form})
