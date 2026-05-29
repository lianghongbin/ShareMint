from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0002_auditlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='bnb_wallet_address',
            field=models.CharField(blank=True, max_length=42, verbose_name='BNB 钱包地址'),
        ),
    ]
