ACCOUNT_URL_NAMES = frozenset({
    'admin_profile',
    'headman_profile',
    'member_profile',
    'settings',
    'settings_change_email',
    'settings_two_factor_setup',
    'settings_two_factor_setup_totp',
    'settings_two_factor_setup_email',
    'change_password',
})

ADMIN_MY_URL_NAMES = frozenset({
    'admin_profile',
    'admin_settings_price',
    'admin_settings_commission',
    'admin_settings_backup',
    'admin_backup',
    'admin_restore',
    'admin_settings_email',
    'admin_settings_audit',
    'admin_settings_audit_detail',
})


def _mobile_tabbar_template(user) -> str:
    if not user.is_authenticated:
        return ''
    if user.is_admin:
        return 'management/admin/_mobile_tabbar.html'
    if user.is_headman:
        return 'management/headman/_mobile_tabbar.html'
    if user.is_member:
        return 'management/member/_mobile_tabbar.html'
    return ''


def app_context(request):
    match = getattr(request, 'resolver_match', None)
    user = getattr(request, 'user', None)
    return {
        'current_url_name': match.url_name if match else '',
        'mobile_tabbar_template': _mobile_tabbar_template(user) if user else '',
        'account_url_names': ACCOUNT_URL_NAMES,
        'admin_my_url_names': ADMIN_MY_URL_NAMES,
        'is_locked': bool(
            user and user.is_authenticated and user.is_headman and user.is_locked
        ),
    }
