from django.urls import path

from . import views

app_name = 'management'

urlpatterns = [
    path('', views.role_dashboard_redirect, name='dashboard'),
    # Admin
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/headmen/', views.admin_headman_list, name='admin_headman_list'),
    path('admin/headmen/create/', views.admin_create_headman, name='admin_create_headman'),
    path('admin/admins/create/', views.admin_create_admin, name='admin_create_admin'),
    path('admin/members/', views.admin_member_list, name='admin_member_list'),
    path('admin/members/import-export/', views.admin_member_import_export, name='admin_member_import_export'),
    path('admin/members/<int:pk>/', views.admin_member_detail, name='admin_member_detail'),
    path('admin/headmen/<int:pk>/', views.admin_headman_detail, name='admin_headman_detail'),
    path('admin/headmen/<int:pk>/toggle-lock/', views.admin_toggle_headman_lock, name='admin_toggle_lock'),
    path('admin/headmen/<int:pk>/reset-password/', views.admin_reset_headman_password, name='admin_reset_headman_password'),
    path('admin/settings/price/', views.admin_settings_price, name='admin_settings_price'),
    path('admin/settings/commission/', views.admin_settings_commission, name='admin_settings_commission'),
    path('admin/settings/backup/', views.admin_settings_backup, name='admin_settings_backup'),
    path('admin/settings/backup/run/', views.admin_backup, name='admin_backup'),
    path('admin/settings/backup/restore/', views.admin_restore, name='admin_restore'),
    path('admin/settings/email/', views.admin_settings_email, name='admin_settings_email'),
    path('admin/settings/audit/', views.admin_settings_audit, name='admin_settings_audit'),
    path('admin/settings/audit/clear/', views.admin_settings_audit_clear, name='admin_settings_audit_clear'),
    path('admin/settings/audit/<int:pk>/', views.admin_settings_audit_detail, name='admin_settings_audit_detail'),
    path('admin/profile/', views.admin_profile, name='admin_profile'),
    path('admin/menu/', views.admin_mobile_menu, name='admin_mobile_menu'),
    # Headman
    path('headman/', views.headman_dashboard, name='headman_dashboard'),
    path('headman/members/', views.headman_member_list, name='headman_member_list'),
    path('headman/members/import-export/', views.headman_member_import_export, name='headman_member_import_export'),
    path('headman/members/<int:pk>/', views.headman_member_detail, name='headman_member_detail'),
    path('headman/investments/add/', views.headman_add_investment, name='headman_add_investment'),
    path('headman/members/<int:pk>/investments/add/', views.headman_add_investment, name='headman_add_member_investment'),
    path('headman/members/add/', views.headman_add_member, name='headman_add_member'),
    path('headman/profile/', views.headman_profile, name='headman_profile'),
    # Member
    path('member/', views.member_dashboard, name='member_dashboard'),
    path('member/investments/', views.member_investments, name='member_investments'),
    path('member/profile/', views.member_profile, name='member_profile'),
]
