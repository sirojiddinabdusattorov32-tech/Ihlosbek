from django.utils import timezone
from django.urls import resolve, Resolver404


class OnlineMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile:
                now = timezone.now()
                if not profile.last_activity or (now - profile.last_activity).seconds > 60:
                    Profile = type(profile)
                    Profile.objects.filter(pk=profile.pk).update(last_activity=now)
        response = self.get_response(request)
        return response
