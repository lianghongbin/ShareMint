from django.urls import path
from django.views.generic import RedirectView

from management import views as mgmt_views

from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('login/2fa/', views.two_factor_verify_view, name='two_factor_verify'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password_view, name='reset_password'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('settings/', views.settings_center_view, name='settings'),
    path('settings/security/', RedirectView.as_view(pattern_name='authentication:settings', permanent=False)),
    path('settings/security/2fa/setup/', views.settings_two_factor_setup_view, name='settings_two_factor_setup'),
    path('settings/security/2fa/setup/totp/', views.settings_two_factor_setup_totp_view, name='settings_two_factor_setup_totp'),
    path('settings/security/2fa/setup/email/', views.settings_two_factor_setup_email_view, name='settings_two_factor_setup_email'),
    path('settings/security/2fa/send-code/', views.settings_two_factor_send_code_view, name='settings_two_factor_send_code'),
    path('settings/security/2fa/disable/', views.settings_two_factor_disable_view, name='settings_two_factor_disable'),
    path('settings/email/change/', views.settings_change_email_view, name='settings_change_email'),
    path('api/me/', views.CurrentUserAPIView.as_view(), name='api_me'),
    path('api/profile/', views.ProfileAPIView.as_view(), name='api_profile'),
    path('api/change-password/', views.PasswordChangeAPIView.as_view(), name='api_change_password'),
    path('oauth/<str:provider>/', mgmt_views.oauth_provider_info, name='oauth_provider'),
]
