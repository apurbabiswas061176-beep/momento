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
    new_username = data.get('username')
    if new_username is not None and new_username.strip():
        user.first_name = new_username.strip()
    if bio is not None:
        user.bio = bio
    user.save()
    dp_url = request.build_absolute_uri(user.profile_pic.url) if user.profile_pic else ''
    return JsonResponse({
        'message': 'Profile updated',
        'profile_pic': dp_url,
        'bio': user.bio,
        'username': user.first_name or user.username.split('@')[0]
    })


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


from datetime import timedelta
from django.utils import timezone

def _get_active_friend_payload(user):
    if user.linked_friend and user.link_expires_at:
        if timezone.now() < user.link_expires_at:
            f = user.linked_friend
            dp_url = f.profile_pic.url if f.profile_pic else '/media/default.jpg'
            return {
                'email': f.email,
                'username': f.first_name or f.username.split('@')[0],
                'dp': dp_url,
                'expires_at': user.link_expires_at.isoformat(),
            'duo_streak': user.duo_streak
            }
        else:
            user.linked_friend = None
            user.link_expires_at = None
            user.duo_streak = 0; user.last_duo_post_date = None; user.last_streak_updated_date = None; user.save(update_fields=['linked_friend', 'link_expires_at', 'duo_streak', 'last_duo_post_date', 'last_streak_updated_date'])
    return None

@csrf_exempt
def api_link_friend(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email = data.get('email', '').strip().lower()
    friend_query = data.get('friend', '').strip().lower()
    duration = data.get('duration', '1_week').strip()

    user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    if duration == 'unlink' or not friend_query:
        user.linked_friend = None
        user.link_expires_at = None
        user.duo_streak = 0; user.last_duo_post_date = None; user.last_streak_updated_date = None; user.save(update_fields=['linked_friend', 'link_expires_at', 'duo_streak', 'last_duo_post_date', 'last_streak_updated_date'])
        return JsonResponse({'message': 'Unlinked', 'linked_friend': None})

    durations = {
        '1_week': timedelta(weeks=1),
        '3_weeks': timedelta(weeks=3),
        '1_month': timedelta(days=30),
    }
    if duration not in durations:
        return JsonResponse({'error': 'Invalid duration'}, status=400)

    friend = (
        CustomUser.objects.filter(email__iexact=friend_query).first()
        or CustomUser.objects.filter(username__iexact=friend_query).first()
        or CustomUser.objects.filter(first_name__iexact=friend_query).first()
    )
    if not friend:
        return JsonResponse({'error': 'Friend account not found'}, status=404)
    if friend.id == user.id:
        return JsonResponse({'error': 'Cannot link with yourself'}, status=400)

    user.linked_friend = friend
    user.link_expires_at = timezone.now() + durations[duration]
    user.duo_streak = 0; user.last_duo_post_date = None; user.last_streak_updated_date = None; user.save(update_fields=['linked_friend', 'link_expires_at', 'duo_streak', 'last_duo_post_date', 'last_streak_updated_date'])

    return JsonResponse({
        'message': 'Friend linked!',
        'linked_friend': _get_active_friend_payload(user)
    })

@csrf_exempt
def api_linked_friend(request):
    email = request.GET.get('email', '').strip().lower()
    if not email and request.method == 'POST':
        try:
            email = json.loads(request.body or '{}').get('email', '').strip().lower()
        except Exception:
            pass
    user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    if not user:
        return JsonResponse({'linked_friend': None})
    return JsonResponse({'linked_friend': _get_active_friend_payload(user)})



from .models import UserMemory

@csrf_exempt
def api_memories(request):
    if request.method == 'GET':
        email = request.GET.get('email', '').strip().lower()
        user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
        if not user:
            return JsonResponse({'memories': []})
        items = [
            {
                'id': m.id,
                'title': m.title,
                'caption': m.caption,
                'image_url': m.image.url if m.image else '',
                'created_at': m.created_at.strftime('%b %d, %Y')
            }
            for m in user.memories.all()
        ]
        return JsonResponse({'memories': items})

    if request.method == 'POST':
        try:
            data = json.loads(request.body or '{}')
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        email = data.get('email', '').strip().lower()
        title = (data.get('title') or 'Memory').strip()[:60]
        caption = (data.get('caption') or '').strip()[:220]
        raw_img = data.get('image') or ''

        user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
        if not user:
            return JsonResponse({'error': 'User not found'}, status=404)
        if not raw_img:
            return JsonResponse({'error': 'Please select a photo for your memory'}, status=400)

        img_file = decode_base64_image(raw_img, prefix='memory')
        if not img_file:
            return JsonResponse({'error': 'Could not process image'}, status=400)

        mem = UserMemory.objects.create(user=user, title=title or 'Memory', caption=caption, image=img_file)
        return JsonResponse({
            'message': 'Memory saved!',
            'memory': {
                'id': mem.id,
                'title': mem.title,
                'caption': mem.caption,
                'image_url': mem.image.url,
                'created_at': mem.created_at.strftime('%b %d, %Y')
            }
        })

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def api_delete_memory(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email = data.get('email', '').strip().lower()
    mem_id = data.get('id')
    user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    deleted, _ = UserMemory.objects.filter(id=mem_id, user=user).delete()
    return JsonResponse({'deleted': bool(deleted)})

# --- FOLLOWERS & DISCOVER API ENDPOINTS ---
def _serialize_follow_user(request, u, viewer=None):
    dp_url = request.build_absolute_uri(u.profile_pic.url) if getattr(u, 'profile_pic', None) else ''
    is_following = viewer.following.filter(id=u.id).exists() if viewer else False
    follows_you = u.following.filter(id=viewer.id).exists() if viewer else False
    return {
        'id': u.id,
        'username': u.first_name or u.username or u.email.split('@')[0],
        'handle': u.username,
        'email': u.email,
        'bio': getattr(u, 'bio', '') or '',
        'mood': getattr(u, 'mood', 'chill') or 'chill',
        'profile_pic': dp_url,
        'followers_count': u.followers.count(),
        'following_count': u.following.count(),
        'is_following': is_following,
        'is_mutual': is_following and follows_you,
    }

@csrf_exempt
def api_follow_toggle(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email = data.get('email', '').strip().lower()
    target_email = data.get('target_email', '').strip().lower()
    target_id = data.get('target_id')

    me = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    if not me:
        return JsonResponse({'error': 'Current user not found'}, status=404)

    target = None
    if target_id:
        target = CustomUser.objects.filter(id=target_id).first()
    if not target and target_email:
        target = CustomUser.objects.filter(email=target_email).first() or CustomUser.objects.filter(username=target_email).first()

    if not target or target.id == me.id:
        return JsonResponse({'error': 'Invalid target user'}, status=400)

    if target.followers.filter(id=me.id).exists():
        target.followers.remove(me)
        following = False
    else:
        target.followers.add(me)
        following = True

    is_mutual = following and me.followers.filter(id=target.id).exists()
    return JsonResponse({
        'following': following,
        'is_mutual': is_mutual,
        'target_followers_count': target.followers.count(),
        'my_following_count': me.following.count(),
        'my_followers_count': me.followers.count(),
    })

@csrf_exempt
def api_follow_list(request):
    email = request.GET.get('email', '').strip().lower()
    viewer_email = request.GET.get('viewer', email).strip().lower()
    user = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    viewer = CustomUser.objects.filter(email=viewer_email).first() or user
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    followers = [_serialize_follow_user(request, u, viewer) for u in user.followers.all()]
    following = [_serialize_follow_user(request, u, viewer) for u in user.following.all()]
    return JsonResponse({
        'followers_count': len(followers),
        'following_count': len(following),
        'followers': followers,
        'following': following,
    })

@csrf_exempt
def api_discover_users(request):
    email = request.GET.get('email', '').strip().lower()
    q = request.GET.get('q', '').strip()
    me = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    qs = CustomUser.objects.all()
    if me:
        qs = qs.exclude(id=me.id)
    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(email__icontains=q)
    users = [_serialize_follow_user(request, u, me) for u in qs.distinct().order_by('-date_joined')[:25]]
    return JsonResponse({'users': users})

from django.db.models import Q
from .models import DirectMessage

@csrf_exempt
def api_messages_threads(request):
    email = request.GET.get('email', '').strip().lower()
    me = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    if not me:
        return JsonResponse({'threads': {}})
    msgs = DirectMessage.objects.filter(Q(sender=me) | Q(recipient=me)).select_related('sender', 'recipient').order_by('created_at')
    threads = {}
    for m in msgs:
        other = m.recipient if m.sender_id == me.id else m.sender
        uname = other.username
        if uname not in threads:
            threads[uname] = []
        threads[uname].append({
            'from': 'me' if m.sender_id == me.id else 'them',
            'text': m.text,
            'created_at': m.created_at.strftime('%H:%M')
        })
    return JsonResponse({'threads': threads})

@csrf_exempt
def api_messages_thread(request):
    email = request.GET.get('email', '').strip().lower()
    other_q = request.GET.get('user', '').strip()
    me = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    other = CustomUser.objects.filter(username__iexact=other_q).first() or CustomUser.objects.filter(email__iexact=other_q).first()
    if not me or not other:
        return JsonResponse({'messages': []})
    msgs = DirectMessage.objects.filter(
        (Q(sender=me) & Q(recipient=other)) | (Q(sender=other) & Q(recipient=me))
    ).order_by('created_at')
    data = [{
        'from': 'me' if m.sender_id == me.id else 'them',
        'text': m.text,
        'created_at': m.created_at.strftime('%H:%M')
    } for m in msgs]
    return JsonResponse({'messages': data, 'username': other.username})

@csrf_exempt
def api_messages_send(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = request.POST
    email = (body.get('email') or '').strip().lower()
    to_user = (body.get('to') or '').strip()
    text = (body.get('text') or '').strip()
    if not text:
        return JsonResponse({'error': 'Empty message'}, status=400)
    me = CustomUser.objects.filter(email=email).first() or CustomUser.objects.filter(username=email).first()
    other = CustomUser.objects.filter(username__iexact=to_user).first() or CustomUser.objects.filter(email__iexact=to_user).first()
    if not me or not other:
        return JsonResponse({'error': 'User not found'}, status=404)
    msg = DirectMessage.objects.create(sender=me, recipient=other, text=text)
    return JsonResponse({'ok': True, 'message': {'from': 'me', 'text': msg.text, 'created_at': msg.created_at.strftime('%H:%M')}})
