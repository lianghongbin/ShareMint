import os
from pathlib import Path

from django.core.management.base import BaseCommand

from authentication.models import Role, User
from management.models import Profile


class Command(BaseCommand):
    help = '初始化系统超级管理员（部署/首次启动时执行，非用户注册）'

    def add_arguments(self, parser):
        parser.add_argument('--username', default=None, help='管理员用户名')
        parser.add_argument('--password', default=None, help='管理员密码')
        parser.add_argument('--reset', action='store_true', help='若已存在则重置密码与权限')

    def handle(self, *args, **options):
        from django.conf import settings

        username = options['username'] or settings.DEFAULT_ADMIN_USERNAME
        password = options['password'] or settings.DEFAULT_ADMIN_PASSWORD
        reset = options['reset']

        user = User.objects.filter(username=username).first()
        if user:
            if not reset:
                self.stdout.write(
                    self.style.WARNING(
                        f'管理员 "{username}" 已存在。如需重置密码请加 --reset'
                    )
                )
                self._print_credentials(username, password, existed=True)
                return
            user.set_password(password)
            self.stdout.write(self.style.WARNING(f'已重置管理员 "{username}" 的密码。'))
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                email=getattr(settings, 'DEFAULT_ADMIN_EMAIL', 'admin@sharemint.local'),
            )
            self.stdout.write(self.style.SUCCESS(f'已创建超级管理员 "{username}"。'))

        user.role = Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.is_first_login = False
        user.save()

        Profile.objects.update_or_create(
            user=user,
            defaults={'name': '系统管理员'},
        )

        self._print_credentials(username, password, existed=False)

    def _print_credentials(self, username, password, existed):
        from django.conf import settings

        port = settings.RUNSERVER_DEFAULT_PORT
        self.stdout.write('')
        self.stdout.write('── 系统管理员（非注册账号，由 init_admin 初始化）──')
        self.stdout.write(f'  登录页: http://127.0.0.1:{port}/auth/login/')
        self.stdout.write(f'  管理台: http://127.0.0.1:{port}/manage/admin/')
        self.stdout.write(f'  用户名: {username}')
        if not existed:
            self.stdout.write(f'  密码:   {password}')
        self.stdout.write('  说明:   普通用户无自助注册，仅 Admin 开户团长、团长录入成员')
        self.stdout.write('')
