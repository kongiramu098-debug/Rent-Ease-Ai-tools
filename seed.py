from django.core.management.base import BaseCommand
from rentals.models import Product, Shop, User


class Command(BaseCommand):
    help = "Create demo users, shops and products."

    def handle(self, *a, **kw):
        owner, _ = User.objects.get_or_create(username="owner1", defaults={"role": "owner", "email": "o@x.com"})
        owner.set_password("demo12345"); owner.save()
        cust, _ = User.objects.get_or_create(username="customer1", defaults={"role": "customer"})
        cust.set_password("demo12345"); cust.save()
        admin, _ = User.objects.get_or_create(username="admin", defaults={
            "role": "admin", "is_staff": True, "is_superuser": True})
        admin.set_password("admin12345"); admin.save()
        s1, _ = Shop.objects.get_or_create(name="TechHire Indiranagar", defaults=dict(
            owner=owner, address="100 Feet Rd, Indiranagar", city="Bengaluru",
            latitude=12.9784, longitude=77.6408, approved=True))
        s2, _ = Shop.objects.get_or_create(name="GadgetLease Koramangala", defaults=dict(
            owner=owner, address="5th Block, Koramangala", city="Bengaluru",
            latitude=12.9352, longitude=77.6245, approved=True))
        items = [
            (s1, "Dell XPS 13", "Laptops", "Dell", "XPS 9310", 450, 5000, 2),
            (s1, "MacBook Air M2", "Laptops", "Apple", "M2", 900, 10000, 1),
            (s1, "Canon EOS 200D", "Cameras", "Canon", "200D", 700, 6000, 2),
            (s2, "Lenovo ThinkPad E14", "Laptops", "Lenovo", "E14", 350, 4000, 3),
            (s2, "Epson Full HD Projector", "Projectors", "Epson", "EB-W06", 800, 7000, 1),
            (s2, "iPad Air", "Tablets", "Apple", "Air 5", 500, 5000, 2),
            (s2, "JBL PartyBox 110", "Speakers", "JBL", "110", 600, 5000, 1),
            (s1, "PlayStation 5", "Gaming consoles", "Sony", "PS5", 650, 8000, 1),
        ]
        for shop, name, cat, brand, model, price, dep, qty in items:
            Product.objects.get_or_create(shop=shop, name=name, defaults=dict(
                category=cat, brand=brand, model=model, daily_price=price,
                security_deposit=dep, quantity=qty, description=f"{brand} {model} available for daily rental."))
        self.stdout.write("Seeded. Logins: customer1/demo12345, owner1/demo12345, admin/admin12345")
