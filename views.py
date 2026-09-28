import json
from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import chatbot
from .forms import RegisterForm
from .models import Booking, Payment, Product, Shop
from .services import create_booking, haversine_km, notify, set_status
import uuid


def home(request):
    return render(request, "rentals/home.html", {
        "categories": [c for c, _ in Product.CATEGORIES],
        "featured": Product.objects.filter(shop__approved=True)[:4]})


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("products")
    return render(request, "rentals/register.html", {"form": form})


def products(request):
    qs = Product.objects.filter(shop__approved=True).select_related("shop")
    q, cat, maxp, city = (request.GET.get(k, "").strip() for k in ("q", "category", "max_price", "city"))
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(model__icontains=q))
    if cat:
        qs = qs.filter(category=cat)
    if maxp.isdigit():
        qs = qs.filter(daily_price__lte=maxp)
    if city:
        qs = qs.filter(shop__city__icontains=city)
    return render(request, "rentals/products.html", {
        "products": qs, "categories": [c for c, _ in Product.CATEGORIES],
        "f": {"q": q, "category": cat, "max_price": maxp, "city": city}})


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("shop"), pk=pk, shop__approved=True)
    quote = None
    if request.method == "POST":
        try:
            start = date.fromisoformat(request.POST.get("start_date", ""))
            end = date.fromisoformat(request.POST.get("end_date", ""))
        except ValueError:
            messages.error(request, "Choose both a start and an end date.")
            return redirect("product", pk=pk)
        if request.user.role != "customer":
            messages.error(request, "Only customer accounts can book.")
            return redirect("product", pk=pk)
        try:
            booking = create_booking(request.user, pk, start, end)
        except ValidationError as e:
            messages.error(request, e.messages[0])
            return redirect("product", pk=pk)
        messages.success(request, f"Booking {booking.booking_ref} created. Pay to secure it.")
        return redirect("payment", pk=booking.pk)
    return render(request, "rentals/product.html", {"p": product, "today": date.today().isoformat()})


@login_required
def payment(request, pk):
    booking = get_object_or_404(Booking, pk=pk, customer=request.user)
    if request.method == "POST" and booking.status in ("PENDING", "CONFIRMED"):
        # MOCK payment. Replace with Razorpay order creation + signature verification.
        Payment.objects.create(booking=booking, amount=booking.grand_total, method="mock",
                               transaction_id="MOCK-" + uuid.uuid4().hex[:12].upper())
        set_status(booking, "PAID", "Payment received (mock)")
        notify(booking.product.shop.owner, f"Payment received for {booking.booking_ref}.")
        messages.success(request, "Payment completed.")
        return redirect("my_bookings")
    return render(request, "rentals/payment.html", {"b": booking})


TIMELINE = ["PENDING", "CONFIRMED", "PAID", "READY", "ACTIVE", "RETURNED", "COMPLETED"]


@login_required
def my_bookings(request):
    rows = []
    for b in request.user.bookings.select_related("product", "product__shop").prefetch_related("events"):
        reached = {e.status for e in b.events.all()}
        steps = [{"label": dict(Booking.STATUSES)[s], "done": s in reached} for s in TIMELINE]
        rows.append({"b": b, "steps": steps, "can_cancel": b.status in ("PENDING", "CONFIRMED"),
                     "can_pay": b.status in ("PENDING", "CONFIRMED")})
    return render(request, "rentals/my_bookings.html", {"rows": rows})


@require_POST
@login_required
def cancel_booking(request, pk):
    b = get_object_or_404(Booking, pk=pk, customer=request.user)
    if b.status in ("PENDING", "CONFIRMED"):
        set_status(b, "CANCELLED", "Cancelled by customer")
        messages.success(request, f"{b.booking_ref} cancelled.")
    else:
        messages.error(request, "This booking can no longer be cancelled.")
    return redirect("my_bookings")


@login_required
def owner_dashboard(request):
    if request.user.role not in ("owner", "admin"):
        return HttpResponseForbidden("Shop owners only.")
    shops = request.user.shops.all()
    bookings = Booking.objects.filter(product__shop__in=shops).select_related("product", "customer")
    earned = sum(p.amount for p in Payment.objects.filter(booking__in=bookings))
    return render(request, "rentals/owner.html", {
        "shops": shops, "bookings": bookings, "statuses": Booking.STATUSES, "earned": earned,
        "products": Product.objects.filter(shop__in=shops)})


@require_POST
@login_required
def update_status(request, pk):
    b = get_object_or_404(Booking, pk=pk, product__shop__owner=request.user)  # owners: own shops only
    status = request.POST.get("status")
    if status in dict(Booking.STATUSES):
        set_status(b, status, request.POST.get("remarks", "")[:200])
    return redirect("owner")


@login_required
def notifications(request):
    items = list(request.user.notifications.all()[:50])
    request.user.notifications.filter(read=False).update(read=True)
    return render(request, "rentals/notifications.html", {"items": items})


def shops_map(request):
    return render(request, "rentals/map.html")


def api_shops_nearby(request):
    qs = Shop.objects.filter(approved=True).prefetch_related("products")
    city = request.GET.get("city", "").strip()
    cat = request.GET.get("category", "").strip()
    if city:
        qs = qs.filter(city__icontains=city)
    if cat:
        qs = qs.filter(products__category=cat).distinct()
    try:
        lat, lng = float(request.GET["lat"]), float(request.GET["lng"])
    except (KeyError, ValueError):
        lat = lng = None
    out = []
    for s in qs:
        item = {"id": s.pk, "name": s.name, "address": s.address, "city": s.city,
                "lat": s.latitude, "lng": s.longitude,
                "categories": sorted({p.category for p in s.products.all()}),
                "distance_km": None}
        if lat is not None:
            item["distance_km"] = round(haversine_km(lat, lng, s.latitude, s.longitude), 1)
        out.append(item)
    if lat is not None:
        out.sort(key=lambda i: i["distance_km"])
    return JsonResponse({"shops": out})


def chat_page(request):
    return render(request, "rentals/chat.html")


@require_POST
def api_chat(request):
    try:
        text = json.loads(request.body).get("message", "").strip()
    except (ValueError, AttributeError):
        return JsonResponse({"error": "Send JSON like {\"message\": \"...\"}."}, status=400)
    if not text or len(text) > 500:
        return JsonResponse({"error": "Message must be 1-500 characters."}, status=400)
    return JsonResponse(chatbot.reply(text))
