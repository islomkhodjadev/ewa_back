from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin

admin.site.unregister(User)


@admin.register(User)
class UserAdmin(ModelAdmin, UserAdmin):
    pass
