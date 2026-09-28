from django.contrib.auth import views as auth
from django.urls import path
from . import views as v

urlpatterns = [
    path("", v.home, name="home"),
    path("login/", auth.LoginView.as_view(template_name="rentals/login.html"), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("register/", v.register, name="register"),
    path("products/", v.products, name="products"),
    path("products/<int:pk>/", v.product_detail, name="product"),
    path("bookings/", v.my_bookings, name="my_bookings"),
    path("bookings/<int:pk>/pay/", v.payment, name="payment"),
    path("bookings/<int:pk>/cancel/", v.cancel_booking, name="cancel"),
    path("owner/", v.owner_dashboard, name="owner"),
    path("owner/bookings/<int:pk>/status/", v.update_status, name="update_status"),
    path("notifications/", v.notifications, name="notifications"),
    path("map/", v.shops_map, name="map"),
    path("chat/", v.chat_page, name="chat"),
    path("api/shops/nearby/", v.api_shops_nearby),
    path("api/ai/chat/", v.api_chat),
]
