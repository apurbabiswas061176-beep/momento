import json
import base64
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from .models import Post, Comment, Story

CustomUser = get_user_model()

def decode_base64_image(data_str, prefix="upload"):
    if not data_str or ";base64," not in data_str:
        return None
    fmt, imgstr = data_str.split(";base64,", 1)
    ext = fmt.split("/")[-1].split("+")[0] or "jpg"
    return ContentFile(base64.b64decode(imgstr), name=f"{prefix}.{ext}")

@login_required(login_url='/login/')
def feed_view(request):
    posts = Post.objects.all()
    stories = Story.objects.filter(created_at__gte=timezone.now() - timedelta(hours=24))
    return render(request, 'posts/feed.html', {'posts': posts, 'stories': stories})

@login_required(login_url='/login/')
def create_post_view(request):
    if request.method == 'POST' and 'image' in request.FILES:
        Post.objects.create(
            author=request.user,
            image=request.FILES['image'],
            caption=request.POST.get('caption', '')
        )
        return redirect('home')
    return render(request, 'posts/create_post.html')

@login_required(login_url='/login/')
def like_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect('home')

@login_required(login_url='/login/')
def add_comment_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            Comment.objects.create(post=post, author=request.user, text=text)
    return redirect('home')

@csrf_exempt
def api_create_post(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if request.content_type and 'multipart/form-data' in request.content_type:
        email = request.POST.get('email', '').strip().lower()
        caption = request.POST.get('caption', '')
        image_file = request.FILES.get('image')
    else:
        data = json.loads(request.body or '{}')
        email = data.get('email', '').strip().lower()
        caption = data.get('caption', '')
        image_file = decode_base64_image(data.get('image'), prefix="post")

    user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    if not user or not image_file:
        return JsonResponse({'error': 'Valid user email and image are required'}, status=400)
    post = Post.objects.create(author=user, image=image_file, caption=caption)
    return JsonResponse({
        'message': 'Post created',
        'id': post.id,
        'caption': post.caption
    })

@csrf_exempt
def api_create_story(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if request.content_type and 'multipart/form-data' in request.content_type:
        email = request.POST.get('email', '').strip().lower()
        image_file = request.FILES.get('image')
    else:
        data = json.loads(request.body or '{}')
        email = data.get('email', '').strip().lower()
        image_file = decode_base64_image(data.get('image'), prefix="story")
    user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    if not user or not image_file:
        return JsonResponse({'error': 'Valid user email and image are required'}, status=400)
    story = Story.objects.create(author=user, image=image_file)
    return JsonResponse({
        'message': 'Story created',
        'id': story.id,
        'image_url': request.build_absolute_uri(story.image.url)
    })

@csrf_exempt
def api_feed(request):
    posts = Post.objects.all()[:50]
    stories = Story.objects.filter(created_at__gte=timezone.now() - timedelta(hours=24))
    return JsonResponse({
        'posts': [{
            'id': p.id,
            'username': p.author.first_name or p.author.username,
            'email': p.author.email,
            'author_dp': request.build_absolute_uri(p.author.profile_pic.url) if p.author.profile_pic else '',
            'image_url': request.build_absolute_uri(p.image.url) if p.image else '',
            'caption': p.caption,
            'likes': p.total_likes(),
            'created_at': p.created_at.isoformat()
        } for p in posts],
        'stories': [{
            'id': s.id,
            'username': s.author.first_name or s.author.username,
            'email': s.author.email,
            'image_url': request.build_absolute_uri(s.image.url) if s.image else '',
            'created_at': s.created_at.isoformat()
        } for s in stories]
    })
