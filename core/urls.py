from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from django.contrib.auth import views as auth_views
from users.views import register_view, profile_view, follow_toggle_view, search_users_view, api_signup, api_login, api_update_dp, api_update_mood, api_link_friend, api_linked_friend, api_memories, api_delete_memory
from posts.views import feed_view, create_post_view, like_post_view, add_comment_view, api_create_post, api_create_story, api_feed
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', feed_view, name='home'),
    path('search/', search_users_view, name='search_users'),
    path('create/', create_post_view, name='create_post'),
    path('like/<int:post_id>/', like_post_view, name='like_post'),
    path('comment/<int:post_id>/', add_comment_view, name='add_comment'),
    path('profile/<str:username>/', profile_view, name='profile'),
    path('follow/<str:username>/', follow_toggle_view, name='follow_toggle'),
    path('register/', register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('api/signup/', api_signup, name='api_signup'),
    path('api/login/', api_login, name='api_login'),
    path('api/update-dp/', api_update_dp, name='api_update_dp'),
    path('api/update-mood/', api_update_mood, name='api_update_mood'),
    path('api/link-friend/', api_link_friend, name='api_link_friend'),
    path('api/linked-friend/', api_linked_friend, name='api_linked_friend'),
    path('api/memories/', api_memories, name='api_memories'),
    path('api/delete-memory/', api_delete_memory, api_follow_toggle, api_follow_list, api_discover_users, name='api_delete_memory'),
    path('api/create-post/', api_create_post, name='api_create_post'),
    path('api/create-story/', api_create_story, name='api_create_story'),
        path('api/follow/toggle/', api_follow_toggle, name='api_follow_toggle'),
    path('api/follow/list/', api_follow_list, name='api_follow_list'),
    path('api/users/discover/', api_discover_users, name='api_discover_users'),
    path('api/feed/', api_feed, name='api_feed'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]


