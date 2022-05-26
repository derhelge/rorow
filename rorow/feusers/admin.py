from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import FeUser

# Define an inline admin descriptor for FeUser model
# which acts a bit like a singleton
class FeUserInline(admin.StackedInline):
    model = FeUser
    can_delete = False
    verbose_name_plural = 'FeUser'
    filter_horizontal = ['kostenstellen']

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (FeUserInline,)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)