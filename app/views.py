import random
import base64
import json
import os
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse, FileResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.views.decorators.cache import cache_page, never_cache
from .models import Car, Profile, Message, Product, Story, Notification, VILOYATLAR, DownloadHistory
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from .serializers import CarSerializer, ProductSerializer, StorySerializer
from .forms import RegisterForm, VerifyForm, LoginForm


_spotify_token = None
_spotify_token_expires = 0


def get_spotify_token():
    global _spotify_token, _spotify_token_expires
    if _spotify_token and timezone.now().timestamp() < _spotify_token_expires:
        return _spotify_token
    client_id = getattr(settings, 'SPOTIFY_CLIENT_ID', '')
    client_secret = getattr(settings, 'SPOTIFY_CLIENT_SECRET', '')
    if not client_id or not client_secret:
        return None
    auth = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
    resp = requests.post('https://accounts.spotify.com/api/token',
        data={'grant_type': 'client_credentials'},
        headers={'Authorization': f'Basic {auth}'})
    if resp.status_code != 200:
        return None
    data = resp.json()
    _spotify_token = data['access_token']
    _spotify_token_expires = timezone.now().timestamp() + data['expires_in'] - 60
    return _spotify_token


@api_view(['GET'])
@permission_classes([AllowAny])
def spotify_search_api(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return Response({'error': 'Query required'}, status=400)
    token = get_spotify_token()
    if not token:
        return Response({'tracks': []})
    resp = requests.get('https://api.spotify.com/v1/search',
        params={'q': query, 'type': 'track', 'limit': 10},
        headers={'Authorization': f'Bearer {token}'})
    if resp.status_code != 200:
        return Response({'error': 'Spotify API xatosi'}, status=resp.status_code)
    data = resp.json()
    tracks = []
    for item in data.get('tracks', {}).get('items', []):
        tracks.append({
            'id': item['id'],
            'name': item['name'],
            'artist': ', '.join(a['name'] for a in item.get('artists', [])),
            'album_image': item['album']['images'][0]['url'] if item.get('album', {}).get('images') else '',
            'duration_ms': item.get('duration_ms', 0),
            'preview_url': item.get('preview_url', ''),
        })
    return Response({'tracks': tracks})


def index(request):
    return render(request, 'splash.html')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def product_list_api(request):
    page = int(request.GET.get('page', 1))
    region = request.GET.get('region', '').strip()
    cache_key = f'products_page_{page}_region_{region or "all"}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)
    qs = Product.objects.select_related('user__profile').prefetch_related(
        Prefetch('likes', queryset=User.objects.all().only('id', 'username', 'first_name')),
        Prefetch('user__stories', queryset=Story.objects.filter(expires_at__gt=timezone.now()).only('id', 'user_id'))
    )
    if region:
        qs = qs.filter(user__profile__region=region)
    offset = (page - 1) * 50
    page_result = qs[offset:offset + 50]
    serializer = ProductSerializer(page_result, many=True, context={'request': request})
    data = serializer.data
    cache.set(cache_key, data, 60)
    return Response(data)


@require_POST
def product_like_api(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    product = get_object_or_404(Product, pk=pk)
    if product.likes.filter(pk=request.user.pk).exists():
        product.likes.remove(request.user)
        liked = False
    else:
        product.likes.add(request.user)
        liked = True
        if product.user != request.user:
            Notification.objects.create(
                recipient=product.user,
                actor=request.user,
                notif_type='like',
                product=product
            )
    return JsonResponse({'liked': liked, 'count': product.likes.count()})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def story_list_api(request):
    cache_key = 'stories_active'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)
    now = timezone.now()
    stories = Story.objects.filter(expires_at__gt=now).select_related('user__profile').prefetch_related(
        Prefetch('viewers', queryset=User.objects.all().only('id')),
        Prefetch('likes', queryset=User.objects.all().only('id', 'username', 'first_name'))
    ).only('id', 'user_id', 'media', 'is_video', 'created_at', 'expires_at',
           'spotify_track_id', 'spotify_track_name', 'spotify_track_artist',
           'spotify_track_image', 'spotify_preview_url', 'music_start_seconds', 'music_duration_seconds')
    serializer = StorySerializer(stories, many=True, context={'request': request})
    data = serializer.data
    cache.set(cache_key, data, 30)
    return Response(data)


@require_POST
def story_view_api(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    story = get_object_or_404(Story, pk=pk)
    if not story.viewers.filter(pk=request.user.pk).exists():
        story.viewers.add(request.user)
    return JsonResponse({'ok': True, 'count': story.viewers.count()})


@require_POST
def story_like_api(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    story = get_object_or_404(Story, pk=pk)
    if story.likes.filter(pk=request.user.pk).exists():
        story.likes.remove(request.user)
        liked = False
    else:
        story.likes.add(request.user)
        liked = True
    return JsonResponse({'liked': liked, 'count': story.likes.count()})


@require_POST
def story_delete_api(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    story = get_object_or_404(Story, pk=pk, user=request.user)
    story.delete()
    return JsonResponse({'ok': True})


@require_POST
def story_upload(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    media = request.FILES.get('media')
    is_video = request.POST.get('is_video') == 'true'
    if not media:
        return JsonResponse({'error': 'no media'}, status=400)
    story = Story.objects.create(
        user=request.user,
        media=media,
        is_video=is_video,
        expires_at=timezone.now() + timezone.timedelta(hours=48)
    )
    spotify_id = request.POST.get('spotify_track_id', '').strip()
    if spotify_id:
        story.spotify_track_id = spotify_id
        story.spotify_track_name = request.POST.get('spotify_track_name', '').strip()
        story.spotify_track_artist = request.POST.get('spotify_track_artist', '').strip()
        story.spotify_track_image = request.POST.get('spotify_track_image', '').strip()
        story.spotify_preview_url = request.POST.get('spotify_preview_url', '').strip()
        try:
            story.music_start_seconds = int(request.POST.get('music_start_seconds', 0))
        except (ValueError, TypeError):
            story.music_start_seconds = 0
        try:
            story.music_duration_seconds = int(request.POST.get('music_duration_seconds', 30))
        except (ValueError, TypeError):
            story.music_duration_seconds = 30
        story.save()
    return JsonResponse({'ok': True})


@require_POST
def story_music_edit(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    story = get_object_or_404(Story, pk=pk, user=request.user)
    spotify_id = request.POST.get('spotify_track_id', '').strip()
    if not spotify_id:
        story.spotify_track_id = None
        story.spotify_track_name = None
        story.spotify_track_artist = None
        story.spotify_track_image = None
        story.spotify_preview_url = None
        story.music_start_seconds = 0
        story.music_duration_seconds = 30
    else:
        story.spotify_track_id = spotify_id
        story.spotify_track_name = request.POST.get('spotify_track_name', '').strip()
        story.spotify_track_artist = request.POST.get('spotify_track_artist', '').strip()
        story.spotify_track_image = request.POST.get('spotify_track_image', '').strip()
        story.spotify_preview_url = request.POST.get('spotify_preview_url', '').strip()
        try:
            story.music_start_seconds = int(request.POST.get('music_start_seconds', 0))
        except (ValueError, TypeError):
            story.music_start_seconds = 0
        try:
            story.music_duration_seconds = int(request.POST.get('music_duration_seconds', 30))
        except (ValueError, TypeError):
            story.music_duration_seconds = 30
    story.save()
    return JsonResponse({'ok': True})


@require_POST
def product_create(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    name = request.POST.get('name') or request.POST.get('car_model') or ''
    price = request.POST.get('price', '')
    mileage = request.POST.get('mileage', '')
    color = request.POST.get('color', '')
    car_model = request.POST.get('car_model', '')
    description = request.POST.get('description', '')
    image = request.FILES.get('image')
    if not name or not image:
        return JsonResponse({'error': 'name and image required'}, status=400)
    Product.objects.create(
        user=request.user,
        name=name,
        price=price,
        mileage=mileage,
        color=color,
        car_model=car_model,
        description=description,
        image=image,
        from_sell_form=True
    )
    return JsonResponse({'ok': True})


def product_add_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        car_model = request.POST.get('car_model', '').strip()
        price = request.POST.get('price', '').strip()
        mileage = request.POST.get('mileage', '').strip()
        color = request.POST.get('color', '').strip()
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image')
        if not car_model or not image:
            messages.error(request, "Moshina rusumi va rasm majburiy!")
            return render(request, 'product_add.html')
        Product.objects.create(
            user=request.user,
            name=car_model,
            price=price,
            mileage=mileage,
            color=color,
            car_model=car_model,
            description=description,
            image=image,
            from_sell_form=True
        )
        messages.success(request, "Mahsulot qo'shildi!")
        return redirect('product_add')
    return render(request, 'product_add.html')


def product_edit_view(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    product = get_object_or_404(Product, pk=pk, user=request.user)
    if request.method == 'POST':
        car_model = request.POST.get('car_model', '').strip()
        price = request.POST.get('price', '').strip()
        mileage = request.POST.get('mileage', '').strip()
        color = request.POST.get('color', '').strip()
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image')
        if not car_model:
            messages.error(request, "Moshina rusumi majburiy!")
            return render(request, 'product_add.html', {'product': product})
        product.name = car_model
        product.car_model = car_model
        product.price = price
        product.mileage = mileage
        product.color = color
        product.description = description
        if image:
            product.image = image
        product.save()
        messages.success(request, "Mahsulot tahrirlandi!")
        return redirect('profile', username=request.user.username)
    return render(request, 'product_add.html', {'product': product})


def product_delete_view(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    product = get_object_or_404(Product, pk=pk, user=request.user)
    product.delete()
    return JsonResponse({'ok': True})

@never_cache
def home(request):
    viloyatlar = [['', "Hamma viloyatlar"]] + [[k, v] for k, v in VILOYATLAR]

    return render(request, 'home.html', {
        'profile_count': 0,
        'online_count': 0,
        'story_users': [],
        'viloyatlar': json.dumps(viloyatlar),
    })


@api_view(['GET'])
def test_api(request):
    return Response({'message': 'API is working!', 'app': 'app'})


class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    pagination_class = None


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            nickname = form.cleaned_data['nickname']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            phone = form.cleaned_data['phone']
            avatar = form.cleaned_data.get('avatar')
            region = form.cleaned_data.get('region', '')

            if User.objects.filter(username=nickname).exists():
                messages.error(request, "Bu nik-name band!")
                return render(request, 'register.html', {'form': form})

            user = User.objects.create_user(username=nickname, email=email, password=password)
            user.is_active = False
            user.save()

            sms_code = str(random.randint(100000, 999999))
            print(f"\n[SMS] {phone} ga kod: {sms_code}\n")

            Profile.objects.create(
                user=user, avatar=avatar, phone=phone,
                region=region, sms_code=sms_code, is_verified=False
            )

            request.session['verify_user_id'] = user.id
            messages.success(request, "Ro'yxatdan o'tdingiz! SMS kodni kiriting.")
            return redirect('verify')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def verify_view(request):
    user_id = request.session.get('verify_user_id')
    if not user_id:
        return redirect('register')

    try:
        profile = Profile.objects.get(user_id=user_id)
    except Profile.DoesNotExist:
        return redirect('register')

    if request.method == 'POST':
        form = VerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            if profile.sms_code == code:
                profile.is_verified = True
                profile.sms_code = None
                profile.save()

                user = profile.user
                user.is_active = True
                user.save()

                login(request, user)
                del request.session['verify_user_id']

                messages.success(request, "Telefon tasdiqlandi! Xush kelibsiz!")
                return redirect('home')
            else:
                messages.error(request, "Noto'g'ri kod! Qayta urinib ko'ring.")
    else:
        form = VerifyForm()

    return render(request, 'verify.html', {'form': form, 'sms_code': profile.sms_code})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            nickname = form.cleaned_data['nickname']
            password = form.cleaned_data['password']
            user = authenticate(request, username=nickname, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Xush kelibsiz, {nickname}!")
                return redirect('home')
            else:
                messages.error(request, "Nik-name yoki parol noto'g'ri!")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def forgot_password_view(request):
    if request.method == 'POST':
        nickname = request.POST.get('nickname', '').strip()
        phone = request.POST.get('phone', '').strip()
        if not nickname or not phone:
            return JsonResponse({'error': 'Nik-name va telefon kiriting!'}, status=400)
        try:
            user = User.objects.get(username=nickname)
            profile = user.profile
        except User.DoesNotExist:
            return JsonResponse({'error': 'Bunday nik-name topilmadi!'}, status=404)
        if profile.phone != phone:
            return JsonResponse({'error': 'Bu telefon ushbu nik-name ga ulanmagan!'}, status=400)
        new_password = str(random.randint(100000, 999999))
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        print(f"\n[SMS] {phone} ga yangi parol: {new_password}\n")
        return JsonResponse({'ok': True, 'message': f'Yangi parolingiz: {new_password}\n(SMS xizmati ulangandan keyin bu telefon nomerga keladi)'})
    return JsonResponse({'error': 'GET so\'rov qabul qilinmaydi'}, status=405)


def logout_view(request):
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile:
            profile.last_activity = None
            profile.save(update_fields=['last_activity'])
    logout(request)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax') or request.POST.get('ajax'):
        return JsonResponse({'ok': True, 'logged_out': True})
    return redirect('index')


from .translations import LANGUAGES_DATA

def set_language(request):
    lang = request.GET.get('lang', 'uz')
    if lang not in LANGUAGES_DATA:
        lang = 'uz'
    request.session['lang'] = lang
    next_url = request.GET.get('next', 'home')
    return redirect(next_url)


def ads_view(request):
    if request.method == 'POST':
        name = request.POST.get('name') or request.POST.get('car_model') or ''
        if not name:
            return JsonResponse({'error': 'name or car_model required'}, status=400)
        location = request.POST.get('location')
        phone = request.POST.get('phone')
        phone2 = request.POST.get('phone2', '')
        image = request.FILES.get('image')
        if name and phone:
            Car.objects.create(name=name, location=location, year=2025, phone=phone, phone2=phone2, image=image, from_sell_form=True)
            messages.success(request, "Reklama qo'shildi!")
            return redirect('ads')

    cars = Car.objects.all().order_by('-created_at')
    return render(request, 'ads.html', {'cars': cars})


def ads_edit(request, pk):
    car = get_object_or_404(Car, pk=pk)
    if request.method == 'POST':
        car.name = request.POST.get('name', car.name)
        car.location = request.POST.get('location', '')
        car.phone = request.POST.get('phone', car.phone)
        car.phone2 = request.POST.get('phone2', '')
        if request.FILES.get('image'):
            car.image = request.FILES['image']
        car.save()
        messages.success(request, "Reklama tahrirlandi!")
        return redirect('ads')
    return render(request, 'ads_edit.html', {'car': car})


def ads_delete(request, pk):
    car = get_object_or_404(Car, pk=pk)
    if request.method == 'POST':
        car.delete()
        messages.success(request, "Reklama o'chirildi!")
        return redirect('ads')
    return render(request, 'ads_delete.html', {'car': car})


def profile_view(request, username):
    user = get_object_or_404(User.objects.select_related('profile'), username=username)

    # ihlosbek1406 profili faqat o'ziga ko'rinadi
    if user.username == 'ihlosbek1406' and (not request.user.is_authenticated or request.user.username != 'ihlosbek1406'):
        return redirect('home')

    profile = user.profile
    sub_count = profile.subscribers.count()
    following_count = profile.following.count()
    products = Product.objects.filter(user=user)
    admin_products = []
    is_subscribed = False
    if request.user.is_authenticated and request.user != user:
        is_subscribed = request.user.profile in profile.subscribers.all()
    return render(request, 'profile.html', {
        'profile_user': user,
        'profile': profile,
        'products': products,
        'admin_products': admin_products,
        'sub_count': sub_count,
        'following_count': following_count,
        'is_subscribed': is_subscribed,
        'VILOYATLAR': dict(VILOYATLAR),
    })


def profile_edit(request):
    if not request.user.is_authenticated:
        return redirect('login')
    profile = request.user.profile
    if request.method == 'POST':
        nickname = request.POST.get('nickname')
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        avatar = request.FILES.get('avatar')
        old_password = request.POST.get('old_password')
        password = request.POST.get('password')

        if password:
            if not old_password:
                messages.error(request, "Eski parolni kiriting!")
                return render(request, 'profile_edit.html', {'profile': profile})
            if not request.user.check_password(old_password):
                messages.error(request, "Eski parol noto'g'ri!")
                return render(request, 'profile_edit.html', {'profile': profile})
            request.user.set_password(password)
            update_session_auth_hash(request, request.user)
        if full_name:
            request.user.first_name = full_name
        if nickname and nickname != request.user.username:
            if User.objects.filter(username=nickname).exclude(pk=request.user.pk).exists():
                messages.error(request, "Bu nik-name band!")
                return render(request, 'profile_edit.html', {'profile': profile})
            else:
                request.user.username = nickname
        region = request.POST.get('region')
        if phone:
            profile.phone = phone
        if region:
            profile.region = region
        if avatar:
            profile.avatar = avatar
        request.user.save()
        profile.save()
        messages.success(request, "Profil yangilandi!")
        return redirect('profile', username=request.user.username)
    return render(request, 'profile_edit.html', {'profile': profile})


@require_POST
def delete_account_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    password = request.POST.get('password', '')
    if not request.user.check_password(password):
        messages.error(request, "Eski parol noto'g'ri!")
        return redirect('profile_edit')
    username = request.user.username
    request.user.delete()
    logout(request)
    messages.success(request, f"@{username} profili o'chirildi!")
    return redirect('home')


def subscribe_view(request, username):
    if not request.user.is_authenticated:
        return redirect('login')
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return redirect('profile', username=username)
    target_profile = target.profile
    user_profile = request.user.profile
    if user_profile in target_profile.subscribers.all():
        target_profile.subscribers.remove(user_profile)
    else:
        target_profile.subscribers.add(user_profile)
        Notification.objects.create(
            recipient=target,
            actor=request.user,
            notif_type='subscribe'
        )
    return redirect('profile', username=username)


def subscribers_list(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
    subscribers = profile.subscribers.all()
    return render(request, 'subscribers_list.html', {'list_title': 'Obunachilar', 'profiles': subscribers})


def following_list(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
    following = profile.following.all()
    return render(request, 'subscribers_list.html', {'list_title': 'Obunalar', 'profiles': following})


def search_view(request):
    q = request.GET.get('q', '').strip()
    profiles = None
    products = None
    if q:
        users = User.objects.filter(username__icontains=q).exclude(username='ihlosbek1406')[:10]
        profiles = Profile.objects.filter(user__in=users)
        products = Product.objects.filter(name__icontains=q)[:20]
    return render(request, 'search.html', {'query': q, 'profiles': profiles, 'products': products})


def search_api(request):
    q = request.GET.get('q', '').strip()
    data = {'profiles': [], 'products': []}
    if q:
        users = User.objects.filter(username__icontains=q).exclude(username='ihlosbek1406')[:10]
        profiles = Profile.objects.filter(user__in=users)
        for p in profiles:
            data['profiles'].append({
                'username': p.user.username,
                'first_name': p.user.first_name,
                'avatar': p.avatar.url if p.avatar else None,
            })
        products = Product.objects.filter(name__icontains=q)[:20]
        for p in products:
            data['products'].append({
                'name': p.name,
                'car_model': p.car_model or p.name,
                'price': str(p.price) if p.price else None,
                'mileage': p.mileage,
                'username': p.user.username,
                'image': p.image.url,
            })
    return JsonResponse(data)


def notifications_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0, 'items': []})
    cache_key = f'notif_{request.user.pk}'
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)
    items = []
    # Get unread messages (SMS)
    unread = Message.objects.filter(receiver=request.user, is_read=False).select_related('sender__profile')
    for msg in unread.order_by('-timestamp')[:10]:
        s = msg.sender
        content = msg.content
        if not content:
            if msg.file_type == 'video':
                content = '🎥 Video xabar'
            elif msg.file_type == 'audio':
                content = '🎵 Ovozli xabar'
            else:
                content = '[Fayl]'
        items.append({
            'id': f'msg_{msg.id}',
            'type': 'message',
            'username': s.username,
            'first_name': s.first_name,
            'avatar': s.profile.avatar.url if s.profile.avatar else None,
            'text': content[:120],
            'time': msg.timestamp.isoformat(),
            'link': f'/chat/{s.username}/',
        })
    # Get subscribe and like notifications
    notifs = Notification.objects.filter(recipient=request.user, is_read=False).select_related('actor__profile', 'product')[:20]
    for n in notifs:
        if n.notif_type == 'subscribe':
            text = f"{n.actor.first_name or n.actor.username} sizga obuna bo'ldi"
            link = f'/profile/{n.actor.username}/'
        elif n.notif_type == 'like':
            product_name = n.product.name if n.product else 'mahsulot'
            text = f"{n.actor.first_name or n.actor.username} mahsulotingizni yoqtirdi: {product_name}"
            link = f'/chat/{n.actor.username}/'
        else:
            continue
        items.append({
            'id': f'notif_{n.id}',
            'type': n.notif_type,
            'username': n.actor.username,
            'first_name': n.actor.first_name,
            'avatar': n.actor.profile.avatar.url if n.actor.profile.avatar else None,
            'text': text,
            'time': n.created_at.isoformat(),
            'link': link,
        })
    items.sort(key=lambda x: x['time'], reverse=True)
    result = {'count': len(items), 'items': items}
    cache.set(cache_key, result, 10)
    return JsonResponse(result)


@require_POST
def mark_notifications_read(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    cache.delete(f'notif_{request.user.pk}')
    return JsonResponse({'ok': True})


def chat_list_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'chats': []})
    cache_key = f'chatlist_{request.user.pk}'
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)
    chat_ids = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).values_list('sender', 'receiver').distinct()[:200]
    user_ids = set()
    for s, r in chat_ids:
        if s == request.user.pk:
            user_ids.add(r)
        else:
            user_ids.add(s)
    chats = []
    for uid in user_ids:
        try:
            other = User.objects.get(pk=uid)
        except User.DoesNotExist:
            continue
        last_msg = Message.objects.filter(
            Q(sender=request.user, receiver=other) |
            Q(sender=other, receiver=request.user)
        ).order_by('-timestamp').first()
        chats.append({
            'username': other.username,
            'first_name': other.first_name,
            'avatar': other.profile.avatar.url if other.profile.avatar else None,
            'last_message': last_msg.content[:60] if last_msg else '',
            'last_time': last_msg.timestamp.strftime('%H:%M') if last_msg else '',
        })
    chats.sort(key=lambda c: c.get('last_time', ''), reverse=True)
    result = {'chats': chats}
    cache.set(cache_key, result, 30)
    return JsonResponse(result)


def chat_view(request, username):
    if not request.user.is_authenticated:
        return redirect('login')
    other = get_object_or_404(User, username=username)
    Message.objects.filter(sender=other, receiver=request.user, is_read=False).update(is_read=True)
    messages_list = Message.objects.filter(
        Q(sender=request.user, receiver=other) |
        Q(sender=other, receiver=request.user)
    ).order_by('timestamp')
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        uploaded_file = request.FILES.get('file')
        file_type = request.POST.get('file_type', '')
        if content:
            Message.objects.create(sender=request.user, receiver=other, content=content)
        if uploaded_file and file_type:
            Message.objects.create(sender=request.user, receiver=other, content='', file=uploaded_file, file_type=file_type)
        cache.delete(f'chatlist_{request.user.pk}')
        cache.delete(f'chatlist_{other.pk}')
        cache.delete(f'notif_{other.pk}')
        return redirect('chat', username=username)
    chats = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).values_list('sender', 'receiver').distinct()
    chat_users = set()
    for s, r in chats:
        if s == request.user.pk:
            chat_users.add(r)
        else:
            chat_users.add(s)
    chat_profiles = Profile.objects.filter(user_id__in=chat_users)
    now = timezone.now()
    return render(request, 'smschat.html', {
        'other': other,
        'other_profile': other.profile,
        'messages': messages_list,
        'chat_profiles': chat_profiles,
        'now': now,
        'now_minus_15': now - timezone.timedelta(minutes=15),
    })


def delete_message(request, msg_id):
    if not request.user.is_authenticated:
        return redirect('login')
    msg = get_object_or_404(Message, pk=msg_id, sender=request.user)
    other = msg.receiver
    msg.delete()
    return redirect('chat', username=other.username)


def react_message(request, msg_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=401)
    msg = get_object_or_404(Message, pk=msg_id)
    emoji = request.POST.get('emoji', '').strip()
    if emoji:
        msg.reaction = emoji
        msg.save()
    return JsonResponse({'reaction': msg.reaction})

def chat_list_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    chats = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).values_list('sender', 'receiver').distinct()[:200]
    user_ids = set()
    for s, r in chats:
        if s == request.user.pk:
            user_ids.add(r)
        else:
            user_ids.add(s)
    chat_users = []
    for uid in user_ids:
        try:
            other = User.objects.get(pk=uid)
        except User.DoesNotExist:
            continue
        last_msg = Message.objects.filter(
            Q(sender=request.user, receiver=other) |
            Q(sender=other, receiver=request.user)
        ).order_by('-timestamp').first()
        chat_users.append({
            'user': other,
            'profile': other.profile,
            'last_message': last_msg.content[:100] if last_msg and last_msg.content else ('📎 Fayl' if last_msg and last_msg.file else ''),
            'last_time': last_msg.timestamp if last_msg else None,
        })
    chat_users.sort(key=lambda c: c['last_time'] or timezone.datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    now = timezone.now()
    return render(request, 'chat_list.html', {
        'chat_users': chat_users,
        'now': now,
        'now_minus_15': now - timezone.timedelta(minutes=15),
    })


def download_apk(request):
    file_path = os.path.join(settings.BASE_DIR, 'downloads', 'avtosotuv-v1.0.0.apk')
    if not os.path.exists(file_path):
        return HttpResponseNotFound("Fayl topilmadi")

    file_size = os.path.getsize(file_path)
    size_str = f"{file_size // (1024*1024)} MB" if file_size > 1024*1024 else f"{file_size // 1024} KB"

    DownloadHistory.objects.create(
        user=request.user if request.user.is_authenticated else None,
        file_name='avtosotuv-v1.0.0.apk',
        file_size=size_str,
        platform='android',
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    response = FileResponse(open(file_path, 'rb'), content_type='application/vnd.android.package-archive')
    response['Content-Disposition'] = 'attachment; filename="avtosotuv-v1.0.0.apk"'
    response['Content-Length'] = file_size
    return response


def download_shortcut(request):
    site_url = 'http://127.0.0.1:8000/'
    content = f'[InternetShortcut]\nURL={site_url}\n'
    file_size = len(content.encode())
    size_str = '1 KB'

    DownloadHistory.objects.create(
        user=request.user if request.user.is_authenticated else None,
        file_name='avtosotuv.uz.url',
        file_size=size_str,
        platform='windows',
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    response = HttpResponse(content, content_type='application/internet-shortcut')
    response['Content-Disposition'] = 'attachment; filename="avtosotuv.uz.url"'
    response['Content-Length'] = file_size
    return response


def download_history_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    downloads = DownloadHistory.objects.filter(user=request.user)[:50]
    return render(request, 'download_history.html', {'downloads': downloads})


@never_cache
def service_worker(request):
    file_path = os.path.join(settings.BASE_DIR, 'static', 'service-worker.js')
    with open(file_path, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/javascript')


def manifest_json(request):
    file_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    with open(file_path, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/manifest+json')