from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from .models import CustomUser

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required(login_url='/login/')
def profile_view(request, username):
    profile_user = get_object_or_404(CustomUser, username=username)
    if request.method == 'POST' and request.user == profile_user:
        profile_user.bio = request.POST.get('bio', '').strip()
        profile_user.save()
        return redirect('profile', username=username)
    posts = profile_user.posts.all()
    is_following = request.user in profile_user.followers.all()
    return render(request, 'users/profile.html', {
        'profile_user': profile_user,
        'posts': posts,
        'is_following': is_following,
    })

@login_required(login_url='/login/')
def follow_toggle_view(request, username):
    target_user = get_object_or_404(CustomUser, username=username)
    if target_user != request.user:
        if request.user in target_user.followers.all():
            target_user.followers.remove(request.user)
        else:
            target_user.followers.add(request.user)
    return redirect('profile', username=username)

@login_required(login_url='/login/')
def search_users_view(request):
    query = request.GET.get('q', '').strip()
    if query:
        users = CustomUser.objects.filter(username__icontains=query).exclude(id=request.user.id)
    else:
        users = CustomUser.objects.exclude(id=request.user.id).order_by('-date_joined')[:20]
    return render(request, 'users/search.html', {'users': users, 'query': query})
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate

@csrf_exempt
def api_signup(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        if not email or not password:
            return JsonResponse({'error': 'Email and password are required'}, status=400)
        if CustomUser.objects.filter(email=email).exists() or CustomUser.objects.filter(username=email).exists():
            return JsonResponse({'error': 'Email is already registered'}, status=400)
        user = CustomUser.objects.create_user(username=email, email=email, password=password)
        if hasattr(user, 'first_name'):
            user.first_name = username
            user.save()
        return JsonResponse({'username': username or email.split('@')[0], 'email': user.email})
    return JsonResponse({'error': 'POST required'}, status=405)

@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        user = authenticate(username=email, password=password)
        if user:
            return JsonResponse({'username': user.first_name or email.split('@')[0], 'email': user.email})
        return JsonResponse({'error': 'Invalid email or password'}, status=401)
    return JsonResponse({'error': 'POST required'}, status=405)
