from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

admin.site.register(User, UserAdmin)
@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "approved")
    list_editable = ("approved",)
admin.site.register([Product, Booking, Payment, Tracking, Notification])
