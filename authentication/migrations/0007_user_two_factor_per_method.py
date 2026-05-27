from django.db import migrations, models


def migrate_two_factor_flags(apps, schema_editor):
    User = apps.get_model('authentication', 'User')
    for user in User.objects.filter(two_factor_enabled=True):
        if user.two_factor_method == 'email':
            user.two_factor_email_enabled = True
        else:
            user.two_factor_totp_enabled = True
        user.save(update_fields=['two_factor_totp_enabled', 'two_factor_email_enabled'])


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0006_passwordhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='two_factor_totp_enabled',
            field=models.BooleanField(default=False, verbose_name='验证器二次验证'),
        ),
        migrations.AddField(
            model_name='user',
            name='two_factor_email_enabled',
            field=models.BooleanField(default=False, verbose_name='邮件二次验证'),
        ),
        migrations.RunPython(migrate_two_factor_flags, migrations.RunPython.noop),
    ]
