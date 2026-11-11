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
        if 'profile_pic' in request.FILES:
            profile_user.profile_pic = request.FILES['profile_pic']
        if 'bio' in request.POST:
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
    if request.user != target_user:
        if request.user in target_user.followers.all():
            target_user.followers.remove(request.user)
        else:
            target_user.followers.add(request.user)
    return redirect('profile', username=username)


@login_required(login_url='/login/')
def search_users_view(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = CustomUser.objects.filter(username__icontains=query)
    return render(request, 'users/search.html', {
        'query': query,
        'results': results,
    })
