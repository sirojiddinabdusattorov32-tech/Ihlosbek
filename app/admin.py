from django.contrib import admin
from .models import Car, Profile, Product, Story

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'year', 'phone', 'created_at')
    search_fields = ('name', 'phone')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'phone', 'region', 'is_verified', 'email')
    search_fields = ('user__username', 'phone')
    list_filter = ('is_verified',)

    def nickname(self, obj):
        return obj.user.username
    nickname.short_description = "Nik-name"

    def email(self, obj):
        return obj.user.email
    email.short_description = "Gmail"

    def region(self, obj):
        return obj.get_region_display()
    region.short_description = "Viloyat"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'user__username')
    list_filter = ('created_at',)


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_video', 'created_at', 'expires_at')
    search_fields = ('user__username',)
    list_filter = ('is_video', 'created_at')
