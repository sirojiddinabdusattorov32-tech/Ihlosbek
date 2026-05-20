
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app.views import index, home, register_view, login_view, logout_view, verify_view, ads_view, ads_edit, ads_delete, profile_view, profile_edit, subscribe_view, subscribers_list, following_list, search_view, chat_view, notifications_api, mark_notifications_read, chat_list_api, delete_message, react_message, product_list_api, story_list_api, story_upload, product_create, product_like_api, story_view_api, story_like_api, story_delete_api, spotify_search_api, story_music_edit, product_add_view, product_edit_view, product_delete_view, download_apk, download_history_view, forgot_password_view, set_language, service_worker, manifest_json

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('app.urls')),
    path('', index, name='index'),
    path('home/', home, name='home'),
    path('register/', register_view, name='register'),
    path('verify/', verify_view, name='verify'),
    path('login/', login_view, name='login'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('logout/', logout_view, name='logout'),
    path('ads/', ads_view, name='ads'),
    path('ads/edit/<int:pk>/', ads_edit, name='ads_edit'),
    path('ads/delete/<int:pk>/', ads_delete, name='ads_delete'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/<str:username>/', profile_view, name='profile'),
    path('subscribe/<str:username>/', subscribe_view, name='subscribe'),
    path('subscribers/<str:username>/', subscribers_list, name='subscribers'),
    path('following/<str:username>/', following_list, name='following'),
    path('search/', search_view, name='search'),
    path('chat/<str:username>/', chat_view, name='chat'),
    path('notifications/', notifications_api, name='notifications'),
    path('notifications/read/', mark_notifications_read, name='mark_notifications_read'),
    path('chat-list/', chat_list_api, name='chat_list'),
    path('msg/delete/<int:msg_id>/', delete_message, name='delete_message'),
    path('msg/react/<int:msg_id>/', react_message, name='react_message'),
    path('api/products/', product_list_api, name='product_list_api'),
    path('api/stories/', story_list_api, name='story_list_api'),
    path('story/upload/', story_upload, name='story_upload'),
    path('product/create/', product_create, name='product_create'),
    path('product/<int:pk>/like/', product_like_api, name='product_like'),
    path('product/add/', product_add_view, name='product_add'),
    path('product/edit/<int:pk>/', product_edit_view, name='product_edit'),
    path('product/delete/<int:pk>/', product_delete_view, name='product_delete'),
    path('story/<int:pk>/view/', story_view_api, name='story_view'),
    path('story/<int:pk>/like/', story_like_api, name='story_like'),
    path('story/<int:pk>/delete/', story_delete_api, name='story_delete'),
    path('story/<int:pk>/music/edit/', story_music_edit, name='story_music_edit'),
    path('api/spotify/search/', spotify_search_api, name='spotify_search'),
    path('download/apk/', download_apk, name='download_apk'),
    path('download/history/', download_history_view, name='download_history'),
    path('set-language/', set_language, name='set_language'),
    path('service-worker.js', service_worker, name='service_worker'),
    path('manifest.json', manifest_json, name='manifest_json'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

