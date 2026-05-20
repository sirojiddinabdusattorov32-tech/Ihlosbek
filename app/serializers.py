from rest_framework import serializers
from .models import Car, Product, Story
from django.contrib.auth.models import User
from django.utils import timezone


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    first_name = serializers.CharField()
    phone = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'avatar', 'phone', 'region']

    def get_avatar(self, obj):
        if hasattr(obj, 'profile') and obj.profile.avatar:
            return obj.profile.avatar.url
        return None

    def get_phone(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.phone
        return None

    def get_region(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.region_display() or obj.profile.region
        return None


class ProductSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    likers = serializers.SerializerMethodField()
    poster_has_stories = serializers.SerializerMethodField()
    poster_has_unviewed = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(pk=request.user.pk).exists()
        return False

    def get_likers(self, obj):
        return UserSerializer(obj.likes.all(), many=True).data

    def get_poster_has_stories(self, obj):
        return Story.objects.filter(user=obj.user, expires_at__gt=timezone.now()).exists()

    def get_poster_has_unviewed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        active = Story.objects.filter(user=obj.user, expires_at__gt=timezone.now())
        if not active.exists():
            return False
        return any(not story.viewers.filter(pk=request.user.pk).exists() for story in active)


class StorySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    view_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    has_viewed = serializers.SerializerMethodField()
    viewers_list = serializers.SerializerMethodField()
    likers_list = serializers.SerializerMethodField()
    music = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = '__all__'

    def get_music(self, obj):
        if obj.spotify_track_id:
            return {
                'track_id': obj.spotify_track_id,
                'track_name': obj.spotify_track_name,
                'artist': obj.spotify_track_artist,
                'album_image': obj.spotify_track_image,
                'preview_url': obj.spotify_preview_url,
                'start_seconds': obj.music_start_seconds,
                'duration_seconds': obj.music_duration_seconds,
            }
        return None

    def get_view_count(self, obj):
        return obj.viewers.count()

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(pk=request.user.pk).exists()
        return False

    def get_has_viewed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.viewers.filter(pk=request.user.pk).exists()
        return False

    def get_viewers_list(self, obj):
        request = self.context.get('request')
        if request and request.user == obj.user:
            return UserSerializer(obj.viewers.all(), many=True).data
        return []

    def get_likers_list(self, obj):
        request = self.context.get('request')
        if request and request.user == obj.user:
            return UserSerializer(obj.likes.all(), many=True).data
        return []
