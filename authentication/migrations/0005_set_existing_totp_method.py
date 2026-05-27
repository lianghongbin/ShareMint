from django.db import migrations


def set_existing_totp_method(apps, schema_editor):
    User = apps.get_model('authentication', 'User')
    User.objects.filter(two_factor_enabled=True).exclude(two_factor_secret='').update(
        two_factor_method='totp',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0004_user_two_factor_method'),
    ]

    operations = [
        migrations.RunPython(set_existing_totp_method, migrations.RunPython.noop),
    ]
