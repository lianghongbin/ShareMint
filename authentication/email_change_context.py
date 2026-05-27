from authentication.constants import EMAIL_CHANGE_PENDING_NEW_KEY, EMAIL_CHANGE_RETURN_KEY
from authentication.email_change import get_current_user_email, is_old_email_verified
from authentication.two_factor import mask_email


def set_email_change_return(request, return_to: str | None) -> None:
    if return_to == 'profile':
        request.session[EMAIL_CHANGE_RETURN_KEY] = 'profile'
    elif return_to == 'settings':
        request.session[EMAIL_CHANGE_RETURN_KEY] = 'settings'
    elif return_to == 'change_email':
        request.session.pop(EMAIL_CHANGE_RETURN_KEY, None)


def get_email_change_redirect_url(request, *, ongoing: bool = False) -> str:
    from django.urls import reverse

    ret = request.session.get(EMAIL_CHANGE_RETURN_KEY)
    user = request.user
    if ret == 'profile':
        if user.is_admin:
            base = reverse('management:admin_profile')
        elif user.is_headman:
            base = reverse('management:headman_profile')
        elif user.is_member:
            base = reverse('management:member_profile')
        else:
            return reverse('authentication:settings_change_email')
        query = '?tab=profile'
        if ongoing:
            query += '&email_change=1'
        return base + query
    if ret == 'settings':
        if user.is_admin:
            return reverse('management:admin_profile') + '?tab=security'
        return reverse('authentication:settings')
    return reverse('authentication:settings_change_email')


def build_email_change_context(request) -> dict:
    current_email = get_current_user_email(request.user)
    has_current_email = bool(current_email)
    if has_current_email and is_old_email_verified(request.session):
        step = 'set_new'
    elif not has_current_email:
        step = 'set_new'
    else:
        step = 'verify_old'

    pending_new = request.session.get(EMAIL_CHANGE_PENDING_NEW_KEY, '')
    return {
        'has_current_email': has_current_email,
        'masked_current_email': mask_email(current_email) if current_email else '',
        'step': step,
        'pending_new_email': pending_new,
        'masked_pending_new_email': mask_email(pending_new) if pending_new else '',
        'email_change_return_to': request.session.get(EMAIL_CHANGE_RETURN_KEY, ''),
    }
