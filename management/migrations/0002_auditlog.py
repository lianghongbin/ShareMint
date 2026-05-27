from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('management', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(blank=True, db_index=True, max_length=150, verbose_name='用户名')),
                ('role', models.CharField(blank=True, max_length=20, verbose_name='角色')),
                ('action', models.CharField(blank=True, db_index=True, max_length=120, verbose_name='动作标识')),
                ('summary', models.CharField(max_length=255, verbose_name='操作摘要')),
                ('detail', models.TextField(blank=True, default='', verbose_name='详情')),
                ('method', models.CharField(max_length=10, verbose_name='请求方法')),
                ('path', models.CharField(max_length=255, verbose_name='请求路径')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP 地址')),
                ('status_code', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='状态码')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='操作时间')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL, verbose_name='操作者')),
            ],
            options={
                'verbose_name': '审计日志',
                'verbose_name_plural': '审计日志',
                'ordering': ['-created_at'],
            },
        ),
    ]
