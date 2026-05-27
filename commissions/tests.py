from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from commissions.constants import GDT_CURRENT_PRICE_KEY
from commissions.models import SystemConfig


class SystemConfigSeedDefaultsTests(TestCase):
    def test_seed_defaults_does_not_overwrite_existing_gdt_price(self):
        SystemConfig.set_value(GDT_CURRENT_PRICE_KEY, '0.16', 'GDT 当前全局唯一价格')

        SystemConfig.seed_defaults()

        self.assertEqual(SystemConfig.get_gdt_price(), Decimal('0.16'))

    def test_migrate_does_not_reset_custom_gdt_price(self):
        SystemConfig.set_value(GDT_CURRENT_PRICE_KEY, '0.16', 'GDT 当前全局唯一价格')

        call_command('migrate', verbosity=0, interactive=False)

        self.assertEqual(SystemConfig.get_gdt_price(), Decimal('0.16'))

    def test_seed_defaults_creates_missing_keys(self):
        SystemConfig.objects.all().delete()

        SystemConfig.seed_defaults()

        self.assertTrue(SystemConfig.objects.filter(key=GDT_CURRENT_PRICE_KEY).exists())
        self.assertEqual(SystemConfig.get_gdt_price(), Decimal('1.00000000'))
