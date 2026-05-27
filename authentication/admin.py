from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Role, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'referrer', 'is_first_login', 'is_locked', 'is_active')
    list_filter = ('role', 'is_first_login', 'is_locked', 'is_active')
    search_fields = ('username', 'email')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('扩展信息', {'fields': ('role', 'is_first_login', 'is_locked', 'referrer')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('扩展信息', {'fields': ('role', 'is_first_login', 'is_locked', 'referrer')}),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.role == Role.MEMBER:
            readonly.append('referrer')
        return readonly
