from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from django.contrib.auth import views as auth_views
from users.views import register_view, profile_view, follow_toggle_view, search_users_view, api_signup, api_login, api_update_dp, api_update_mood
from posts.views import feed_view, create_post_view, like_post_view, add_comment_view, api_create_post, api_create_story, api_feed
from django.conf import settings
urlpatterns = [
path('admin/', admin.site.urls),
path('', feed_view, name='home'),
path('search/', search_users_view, name='search_users'),
path('create/', create_post_view, name='create_post'),
path('like/int:post_id/', like_post_view, name='like_post'),
path('comment/int:post_id/', add_comment_view, name='add_comment'),
path('profile/str:username/', profile_view, name='profile'),
path('follow/str:username/', follow_toggle_view, name='follow_toggle'),
path('register/', register_view, name='register'),
path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
path('logout/', auth_views.LogoutView.as_view(), name='logout'),
path('api/signup/', api_signup, name='api_signup'),
path('api/login/', api_login, name='api_login'),
path('api/update-dp/', api_update_dp, api_update_mood, name='api_update_dp, api_update_mood'),
path('api/create-post/', api_create_post, name='api_create_post'),
path('api/create-story/', api_create_story, name='api_create_story'),
path('api/feed/', api_feed, name='api_feed'),
re_path(r'^media/(?P.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

