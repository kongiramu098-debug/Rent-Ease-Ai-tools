import math
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Booking, Notification, Product, Tracking


def notify(user, message):
    Notification.objects.create(user=user, message=message)


def set_status(booking, status, remarks=""):
    booking.status = status
    booking.save(update_fields=["status"])
    Tracking.objects.create(booking=booking, status=status, remarks=remarks)
    label = booking.get_status_display()
    notify(booking.customer, f"{booking.booking_ref}: {label}")


def create_booking(customer, product_id, start, end):
    if end < start:
        raise ValidationError("End date must be on or after the start date.")
    if start < date.today():
        raise ValidationError("Start date cannot be in the past.")
    days = (end - start).days + 1
    with transaction.atomic():
        product = Product.objects.select_for_update().get(pk=product_id)
        if not product.is_available(start, end):
            raise ValidationError("This product is not available for the chosen dates.")
        booking = Booking.objects.create(
            customer=customer, product=product, start_date=start, end_date=end,
            rental_days=days, rental_total=product.daily_price * days,
            deposit=product.security_deposit)
        Tracking.objects.create(booking=booking, status="PENDING", remarks="Booking created")
        notify(customer, f"{booking.booking_ref}: booking created, awaiting shop confirmation.")
        notify(product.shop.owner, f"New booking {booking.booking_ref} for {product.name}.")
    return booking


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(a))
