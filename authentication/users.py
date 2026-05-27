from authentication.models import User


def is_username_taken(username: str) -> bool:
    value = username.strip()
    if not value:
        return False
    return User.objects.filter(username__iexact=value).exists()
