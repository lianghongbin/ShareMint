from django.contrib import admin

from authentication.models import Role

from .models import AuditLog, Investment, Profile


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'username', 'summary', 'method', 'path', 'ip_address', 'status_code')
    list_filter = ('role', 'method', 'status_code')
    search_fields = ('username', 'summary', 'action', 'path', 'ip_address')
    readonly_fields = (
        'user', 'username', 'role', 'action', 'summary', 'detail',
        'method', 'path', 'ip_address', 'status_code', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.role == Role.MEMBER:
            return ('name',)
        return ()


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'phone', 'wechat', 'email')
    search_fields = ('name', 'user__username', 'phone', 'email')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.user.role == Role.MEMBER:
            return ('name',)
        return ()


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'investment_date',
        'investment_amount',
        'holding_quantity',
        'holding_currency',
    )
    list_filter = ('holding_currency',)
    search_fields = ('user__username',)
