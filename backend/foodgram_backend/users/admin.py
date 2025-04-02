from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import MyUser, Subscription

UserAdmin.fieldsets += (
    ('Extra Fields', {'fields': ('avatar',)}),
)

admin.site.register(MyUser, UserAdmin)
admin.site.register(Subscription)
