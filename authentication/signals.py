from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from authentication.models import Role


@receiver(post_migrate)
def create_role_groups(sender, **kwargs):
    if sender.name != 'authentication':
        return

    role_permissions = {
        Role.ADMIN: Permission.objects.filter(
            codename__in=[
                'add_user',
                'change_user',
                'view_user',
                'add_profile',
                'change_profile',
                'view_profile',
                'add_investment',
                'change_investment',
                'view_investment',
            ]
        ),
        Role.HEADMAN: Permission.objects.filter(
            codename__in=[
                'add_profile',
                'change_profile',
                'view_profile',
                'add_investment',
                'change_investment',
                'view_investment',
            ]
        ),
        Role.MEMBER: Permission.objects.filter(
            codename__in=[
                'change_profile',
                'view_profile',
                'view_investment',
            ]
        ),
    }

    for role, perms in role_permissions.items():
        group, _ = Group.objects.get_or_create(name=role.label)
        group.permissions.set(perms)
