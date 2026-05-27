from django.db.models.signals import post_migrate
from django.dispatch import receiver

from commissions.models import SystemConfig


@receiver(post_migrate)
def seed_system_config(sender, **kwargs):
    if sender.name != 'commissions':
        return
    SystemConfig.seed_defaults()
