from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0005_set_existing_totp_method'),
    ]

    operations = [
        migrations.CreateModel(
            name='PasswordHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='密码哈希')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='记录时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_history', to='authentication.user', verbose_name='用户')),
            ],
            options={
                'verbose_name': '密码历史',
                'verbose_name_plural': '密码历史',
                'ordering': ['-created_at'],
            },
        ),
    ]
