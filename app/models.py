from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Car(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nomi")
    price = models.CharField(max_length=100, verbose_name="Narxi", blank=True, null=True)
    location = models.CharField(max_length=255, verbose_name="Joylashuv", blank=True, null=True)
    year = models.IntegerField(verbose_name="Yili")
    phone = models.CharField(max_length=50, verbose_name="Telefon")
    phone2 = models.CharField(max_length=50, verbose_name="Qo'shimcha telefon", blank=True, null=True)
    image = models.ImageField(upload_to='cars/', verbose_name="Rasm")
    created_at = models.DateTimeField(auto_now_add=True)
    from_sell_form = models.BooleanField(default=False, verbose_name="Sotish formasi orqali")

    class Meta:
        verbose_name = "Avtomobil"
        verbose_name_plural = "Avtomobillar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='car_created_idx'),
            models.Index(fields=['name'], name='car_name_idx'),
        ]

    def __str__(self):
        return self.name


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(verbose_name="Xabar", blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True, verbose_name="Fayl")
    file_type = models.CharField(max_length=10, blank=True, null=True, verbose_name="Fayl turi")
    reaction = models.CharField(max_length=10, blank=True, null=True, verbose_name="Reaksiya")
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['sender', 'receiver', 'timestamp'], name='msg_chat_idx'),
            models.Index(fields=['receiver', 'is_read', 'timestamp'], name='msg_notif_idx'),
            models.Index(fields=['-timestamp'], name='msg_time_idx'),
        ]

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.content[:30]}"


VILOYATLAR = [
    ('qoraqalpogiston', "Qoraqalpog'iston"),
    ('andijon', 'Andijon'),
    ('buxoro', 'Buxoro'),
    ('jizzax', 'Jizzax'),
    ('qashqadaryo', 'Qashqadaryo'),
    ('navoiy', 'Navoiy'),
    ('namangan', 'Namangan'),
    ('samarqand', 'Samarqand'),
    ('surxondaryo', 'Surxondaryo'),
    ('sirdaryo', "Sirdaryo"),
    ('toshkent', 'Toshkent viloyati'),
    ('fargona', "Farg'ona"),
    ('xorazm', 'Xorazm'),
    ('toshkent_sh', 'Toshkent shahri'),
]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Rasm")
    phone = models.CharField(max_length=20, verbose_name="Telefon")
    region = models.CharField(max_length=50, choices=VILOYATLAR, blank=True, null=True, verbose_name="Viloyat")
    sms_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="SMS kod")
    is_verified = models.BooleanField(default=False, verbose_name="Tasdiqlangan")
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name="Oxirgi faollik")
    subscribers = models.ManyToManyField('self', symmetrical=False, related_name='following', blank=True, verbose_name="Obunachilar")

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profillar"
        indexes = [
            models.Index(fields=['phone'], name='prof_phone_idx'),
            models.Index(fields=['last_activity'], name='prof_online_idx'),
            models.Index(fields=['region'], name='prof_region_idx'),
            models.Index(fields=['is_verified'], name='prof_verified_idx'),
        ]

    def __str__(self):
        return self.user.username

    def region_display(self):
        return dict(VILOYATLAR).get(self.region, '')


class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products', verbose_name="Foydalanuvchi")
    name = models.CharField(max_length=255, verbose_name="Nomi")
    price = models.CharField(max_length=100, verbose_name="Narxi", blank=True, null=True)
    car_model = models.CharField(max_length=255, verbose_name="Moshina rusumi", blank=True, null=True)
    mileage = models.CharField(max_length=100, verbose_name="Probeg", blank=True, null=True)
    year = models.IntegerField(verbose_name="Yili", blank=True, null=True)
    color = models.CharField(max_length=100, verbose_name="Kraska sepilgan", blank=True, null=True)
    description = models.TextField(verbose_name="Tavsif", blank=True, null=True)
    image = models.ImageField(upload_to='products/', verbose_name="Rasm")
    likes = models.ManyToManyField(User, related_name='liked_products', blank=True, verbose_name="Yoqtirganlar")
    created_at = models.DateTimeField(auto_now_add=True)
    from_sell_form = models.BooleanField(default=False, verbose_name="Sotish formasi orqali")

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='prod_user_idx'),
            models.Index(fields=['name'], name='prod_name_idx'),
            models.Index(fields=['-created_at'], name='prod_created_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Story(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories', verbose_name="Foydalanuvchi")
    media = models.FileField(upload_to='stories/', verbose_name="Media (rasm/video)")
    is_video = models.BooleanField(default=False, verbose_name="Video")
    viewers = models.ManyToManyField(User, related_name='viewed_stories', blank=True, verbose_name="Ko'rganlar")
    likes = models.ManyToManyField(User, related_name='liked_stories', blank=True, verbose_name="Yoqtirganlar")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Tugash vaqti")
    spotify_track_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="Spotify trek ID")
    spotify_track_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Qo'shiq nomi")
    spotify_track_artist = models.CharField(max_length=255, blank=True, null=True, verbose_name="Artist")
    spotify_track_image = models.URLField(blank=True, null=True, verbose_name="Album rasmi")
    spotify_preview_url = models.URLField(blank=True, null=True, verbose_name="Spotify preview URL")
    music_start_seconds = models.IntegerField(default=0, verbose_name="Boshlanish vaqti (sekund)")
    music_duration_seconds = models.IntegerField(default=30, verbose_name="Davomiylik (sekund)")

    class Meta:
        verbose_name = "Story"
        verbose_name_plural = "Storylar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'expires_at'], name='story_active_idx'),
            models.Index(fields=['-created_at'], name='story_created_idx'),
            models.Index(fields=['expires_at'], name='story_expires_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            self.expires_at = timezone.now() + timezone.timedelta(hours=48)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Notification(models.Model):
    NOTIF_TYPES = [
        ('subscribe', 'Obuna'),
        ('like', 'Like'),
        ('message', 'Xabar'),
    ]
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="Qabul qiluvchi")
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actor_notifications', verbose_name="Kimdan")
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES, verbose_name="Tur")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications', verbose_name="Mahsulot")
    message_preview = models.CharField(max_length=200, blank=True, null=True, verbose_name="Xabar matni")
    is_read = models.BooleanField(default=False, verbose_name="O'qilgan")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Vaqt")

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at'], name='notif_recipient_idx'),
            models.Index(fields=['recipient', 'is_read'], name='notif_unread_idx'),
        ]

    def __str__(self):
        return f"{self.actor.username} -> {self.recipient.username}: {self.notif_type}"


class DownloadHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Foydalanuvchi")
    file_name = models.CharField(max_length=255, verbose_name="Fayl nomi")
    file_size = models.CharField(max_length=50, verbose_name="Fayl hajmi")
    platform = models.CharField(max_length=50, verbose_name="Platforma")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP manzil")
    downloaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuklab olingan vaqt")

    class Meta:
        verbose_name = "Yuklab olish tarixi"
        verbose_name_plural = "Yuklab olish tarixi"
        ordering = ['-downloaded_at']
        indexes = [
            models.Index(fields=['-downloaded_at'], name='dload_time_idx'),
            models.Index(fields=['user'], name='dload_user_idx'),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.downloaded_at.strftime('%Y-%m-%d %H:%M')}"
