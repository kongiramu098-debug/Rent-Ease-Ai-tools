from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [("customer", "Customer"), ("owner", "Shop owner"), ("admin", "Administrator")]
    role = models.CharField(max_length=10, choices=ROLES, default="customer")
    phone = models.CharField(max_length=15, blank=True)


class Shop(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shops")
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=80, db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    approved = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Product(models.Model):
    CATEGORIES = [(c, c) for c in [
        "Laptops", "Smartphones", "Cameras", "Tablets", "Projectors",
        "Speakers", "Gaming consoles", "Computer accessories"]]
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=30, choices=CATEGORIES, db_index=True)
    brand = models.CharField(max_length=60)
    model = models.CharField(max_length=60, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    daily_price = models.DecimalField(max_digits=8, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(daily_price__gt=0), name="price_positive")]

    def __str__(self):
        return self.name

    def is_available(self, start, end):
        busy = self.bookings.filter(start_date__lte=end, end_date__gte=start).exclude(
            status__in=Booking.INACTIVE).count()
        return busy < self.quantity


class Booking(models.Model):
    STATUSES = [
        ("PENDING", "Booking Pending"), ("CONFIRMED", "Booking Confirmed"),
        ("PAID", "Payment Completed"), ("READY", "Ready for Pickup"),
        ("DELIVERY", "Out for Delivery"), ("ACTIVE", "Rental Active"),
        ("RETURN_REQ", "Return Requested"), ("RETURNED", "Returned"),
        ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled"),
    ]
    INACTIVE = ["CANCELLED", "RETURNED", "COMPLETED"]
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="bookings")
    start_date = models.DateField()
    end_date = models.DateField()
    rental_days = models.PositiveIntegerField()
    rental_total = models.DecimalField(max_digits=10, decimal_places=2)
    deposit = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=12, choices=STATUSES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "start_date", "end_date"])]

    @property
    def booking_ref(self):
        return f"RE-{self.pk:06d}"

    @property
    def grand_total(self):
        return self.rental_total + self.deposit


class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, default="mock")
    transaction_id = models.CharField(max_length=60, unique=True)
    status = models.CharField(max_length=12, default="SUCCESS")
    created_at = models.DateTimeField(auto_now_add=True)


class Tracking(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=12, choices=Booking.STATUSES)
    remarks = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["updated_at", "id"]


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
