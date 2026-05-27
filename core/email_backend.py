from django.core.mail.backends.base import BaseEmailBackend

from management.services.email_config import build_email_connection


class SystemConfigEmailBackend(BaseEmailBackend):
    """根据系统配置（SystemConfig）或环境变量发送邮件。"""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        connection = build_email_connection()
        return connection.send_messages(email_messages)
