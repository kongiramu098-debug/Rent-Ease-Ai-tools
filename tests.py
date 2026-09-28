import json
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Booking, Product, Shop, User
from .services import create_booking


class Base(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("o", password="pw12345678", role="owner")
        self.cust = User.objects.create_user("c", password="pw12345678")
        self.other = User.objects.create_user("c2", password="pw12345678")
        shop = Shop.objects.create(owner=self.owner, name="S", address="a", city="X",
                                   latitude=1, longitude=1, approved=True)
        self.p = Product.objects.create(shop=shop, name="Laptop A", category="Laptops", brand="B",
                                        daily_price=400, security_deposit=1000, quantity=1)
        self.d = date.today() + timedelta(days=2)


class BookingTests(Base):
    def test_total_is_price_times_days(self):
        b = create_booking(self.cust, self.p.pk, self.d, self.d + timedelta(days=2))
        self.assertEqual((b.rental_days, b.rental_total, b.deposit), (3, 1200, 1000))

    def test_end_before_start_rejected(self):
        with self.assertRaises(ValidationError):
            create_booking(self.cust, self.p.pk, self.d, self.d - timedelta(days=1))

    def test_double_booking_prevented(self):
        create_booking(self.cust, self.p.pk, self.d, self.d + timedelta(days=1))
        with self.assertRaises(ValidationError):
            create_booking(self.other, self.p.pk, self.d + timedelta(days=1), self.d + timedelta(days=3))

    def test_cancelled_frees_stock(self):
        b = create_booking(self.cust, self.p.pk, self.d, self.d)
        b.status = "CANCELLED"; b.save()
        create_booking(self.other, self.p.pk, self.d, self.d)


class AccessTests(Base):
    def test_register_and_login(self):
        r = self.client.post("/register/", {"username": "new", "email": "n@x.com", "phone": "1",
                                            "role": "customer", "password1": "Str0ngPass!9", "password2": "Str0ngPass!9"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(username="new").exists())

    def test_cannot_open_others_payment_page(self):
        b = create_booking(self.cust, self.p.pk, self.d, self.d)
        self.client.login(username="c2", password="pw12345678")
        self.assertEqual(self.client.get(f"/bookings/{b.pk}/pay/").status_code, 404)

    def test_owner_cannot_update_other_shops_booking(self):
        b = create_booking(self.cust, self.p.pk, self.d, self.d)
        User.objects.create_user("o2", password="pw12345678", role="owner")
        self.client.login(username="o2", password="pw12345678")
        r = self.client.post(f"/owner/bookings/{b.pk}/status/", {"status": "ACTIVE"})
        self.assertEqual(r.status_code, 404)

    def test_payment_marks_paid_and_tracks(self):
        b = create_booking(self.cust, self.p.pk, self.d, self.d)
        self.client.login(username="c", password="pw12345678")
        self.client.post(f"/bookings/{b.pk}/pay/")
        b.refresh_from_db()
        self.assertEqual(b.status, "PAID")
        self.assertEqual(b.payments.count(), 1)
        self.assertEqual(b.events.count(), 2)


class ChatTests(Base):
    def post(self, body):
        return self.client.post("/api/ai/chat/", body, content_type="application/json")

    def test_finds_laptop_within_budget(self):
        r = self.post(json.dumps({"message": "I need a laptop for three days under 500"}))
        data = r.json()
        self.assertEqual(data["intent"], {"category": "Laptops", "days": 3, "budget": 500})
        self.assertEqual(data["products"][0]["total"], "1200.00")

    def test_budget_excludes_products(self):
        r = self.post(json.dumps({"message": "laptop under 100 per day"}))
        self.assertEqual(r.json()["products"], [])

    def test_bad_input_errors(self):
        self.assertEqual(self.post("not json").status_code, 400)
        self.assertEqual(self.post(json.dumps({"message": ""})).status_code, 400)
