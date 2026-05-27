from authentication.two_factor import get_user_notification_email, mask_email


def build_settings_context(user) -> dict:
    notification_email = get_user_notification_email(user)
    return {
        'two_factor_enabled': user.two_factor_enabled,
        'two_factor_method': user.two_factor_method,
        'two_factor_totp_enabled': user.two_factor_totp_enabled,
        'two_factor_email_enabled': user.two_factor_email_enabled,
        'two_factor_method_label': user.get_two_factor_method_display_label(),
        'notification_email': mask_email(notification_email) if notification_email else '',
        'has_notification_email': bool(notification_email),
    }
