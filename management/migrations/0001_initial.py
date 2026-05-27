from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='姓名')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='手机号')),
                ('wechat', models.CharField(blank=True, max_length=50, verbose_name='微信号')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='邮箱')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '用户档案',
                'verbose_name_plural': '用户档案',
            },
        ),
        migrations.CreateModel(
            name='Investment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('investment_date', models.DateTimeField(verbose_name='投资时间')),
                ('investment_amount', models.DecimalField(decimal_places=2, max_digits=18, verbose_name='投资金额 (USDT)')),
                ('holding_quantity', models.DecimalField(decimal_places=8, max_digits=18, verbose_name='持有数量')),
                ('holding_currency', models.CharField(default='GDT', max_length=10, verbose_name='持有币种')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(limit_choices_to={'role': 'member'}, on_delete=django.db.models.deletion.CASCADE, related_name='investments', to=settings.AUTH_USER_MODEL, verbose_name='成员')),
            ],
            options={
                'verbose_name': '投资记录',
                'verbose_name_plural': '投资记录',
                'ordering': ['-investment_date'],
            },
        ),
    ]
