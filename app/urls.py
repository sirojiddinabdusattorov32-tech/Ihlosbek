from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'cars', views.CarViewSet)

urlpatterns = [
    path('test/', views.test_api),
    path('', include(router.urls)),
    path('', views.index),

]
