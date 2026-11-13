import json
import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from .forms import CustomUserCreationForm

CustomUser = get_user_model()

def decode_base64_image(data_str, prefix="img"):
    if not data_str or ";base64," not in data_str:
        return None
    fmt, imgstr = data_str.split(";base64,", 1)
    ext = fmt.split("/")[-1].split("+")[0] or "jpg"
    return ContentFile(base64.b64decode(imgstr), name=f"{prefix}.{ext}")

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required(login_url='/login/')
def profile_view(request, username):
    profile_user = get_object_or_404(CustomUser, username=username)
    if request.method == 'POST' and request.user == profile_user:
        if 'profile_pic' in request.FILES:
            profile_user.profile_pic = request.FILES['profile_pic']
        bio = request.POST.get('bio')
        if bio is not None:
            profile_user.bio = bio
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
            dp_url = request.build_absolute_uri(user.profile_pic.url) if user.profile_pic else ''
            return JsonResponse({
                'username': user.first_name or email.split('@')[0],
                'email': user.email,
                'bio': user.bio,
                'mood': user.mood or 'chill',
                'profile_pic': dp_url
            })
        return JsonResponse({'error': 'Invalid email or password'}, status=401)
    return JsonResponse({'error': 'POST required'}, status=405)

@csrf_exempt
def api_update_dp(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if request.content_type and 'multipart/form-data' in request.content_type:
        email = request.POST.get('email', '').strip().lower()
        image_file = request.FILES.get('profile_pic') or request.FILES.get('image') or request.FILES.get('dp')
        bio = request.POST.get('bio')
    else:
        data = json.loads(request.body or '{}')
        email = data.get('email', '').strip().lower()
        raw_img = data.get('profile_pic') or data.get('image') or data.get('dp')
        image_file = decode_base64_image(raw_img, prefix="dp")
        bio = data.get('bio')

    user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    if image_file:
        user.profile_pic = image_file
    if bio is not None:
        user.bio = bio
    user.save()
    dp_url = request.build_absolute_uri(user.profile_pic.url) if user.profile_pic else ''
    return JsonResponse({'message': 'Profile updated', 'profile_pic': dp_url, 'bio': user.bio})


@csrf_exempt
def api_update_mood(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email = data.get('email', '').strip().lower()
    mood = data.get('mood', 'chill').strip().lower()

    valid_moods = {'chill', 'hyped', 'focused', 'nostalgic', 'night_owl'}
    if mood not in valid_moods:
        return JsonResponse({'error': 'Invalid mood'}, status=400)

    user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    user.mood = mood
    user.save()
    return JsonResponse({'message': 'Mood updated', 'mood': user.mood})
