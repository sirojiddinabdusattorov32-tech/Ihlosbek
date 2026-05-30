from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from app.models import Car, Product, Profile
import requests


class Command(BaseCommand):
    help = 'Seeds database with sample data'

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username='ihlosbek1406',
            defaults={'first_name': 'Ihlosbek'}
        )
        if created:
            user.set_password('biloldinov2010')
            user.save()
            Profile.objects.create(user=user, phone='+998901234567', is_verified=True)
            self.stdout.write(self.style.SUCCESS('Created user ihlosbek1406'))
        else:
            self.stdout.write('User ihlosbek1406 already exists')

        if Car.objects.count() == 0:
            self._create_cars()
        else:
            self.stdout.write('Cars already exist')

        if Product.objects.count() == 0:
            self._create_products()
        else:
            updated = Product.objects.filter(color__isnull=True).update(color='Oq')
            if updated:
                self.stdout.write(f'Updated {updated} products with color')
            self.stdout.write('Products already exist')

    def _create_cars(self):
        try:
            resp = requests.get('https://picsum.photos/400/300', timeout=15)
            cars_data = [
                ('Chevrolet Malibu', '30000$', '+998901234567', 2024),
                ('BMW X5', '50000$', '+998901234568', 2023),
                ('Toyota Camry', '35000$', '+998901234569', 2024),
            ]
            for i, (name, price, phone, year) in enumerate(cars_data):
                img = ContentFile(resp.content, name=f'car_{i}.jpg')
                Car.objects.create(
                    name=name, price=price, year=year,
                    phone=phone, image=img,
                    location='41.2995,69.2401'
                )
            self.stdout.write(self.style.SUCCESS(f'Created {len(cars_data)} cars'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not create cars: {e}'))

    def _create_products(self):
        try:
            u = User.objects.filter(username='ihlosbek1406').first()
            if not u:
                return
            resp = requests.get('https://picsum.photos/300/300', timeout=15)
            products_data = [
                ('Chevrolet Malibu 2.0 Turbo', '28000$', 'Malibu', '50000 km', 'Oq'),
                ('BMW X5 3.0d', '45000$', 'X5', '60000 km', 'Qora'),
                ('Toyota Camry 70', '32000$', 'Camry', '40000 km', 'Kumush'),
            ]
            for i, (name, price, car_model, mileage, color) in enumerate(products_data):
                img = ContentFile(resp.content, name=f'product_{i}.jpg')
                Product.objects.create(
                    user=u, name=name, price=price,
                    car_model=car_model, mileage=mileage,
                    color=color, image=img, description='A\'lo holatda'
                )
            self.stdout.write(self.style.SUCCESS(f'Created {len(products_data)} products'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not create products: {e}'))
