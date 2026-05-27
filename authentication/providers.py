"""第三方 OAuth / Telegram WebApp 登录预留接口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OAuthUserInfo:
    provider: str
    external_id: str
    username: str
    email: str = ''


class OAuthProvider(ABC):
    provider_name: str = 'base'

    @abstractmethod
    def get_authorization_url(self, redirect_uri: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def exchange_token(self, code: str, redirect_uri: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_user_info(self, access_token: str) -> OAuthUserInfo:
        raise NotImplementedError


class TelegramWebAppProvider(OAuthProvider):
    """Telegram WebApp 登录预留实现。"""

    provider_name = 'telegram'

    def get_authorization_url(self, redirect_uri: str) -> str:
        return f'/auth/oauth/telegram/callback/?redirect_uri={redirect_uri}'

    def exchange_token(self, code: str, redirect_uri: str) -> str:
        raise NotImplementedError('Telegram WebApp token 交换尚未接入，请使用账号密码登录。')

    def get_user_info(self, access_token: str) -> OAuthUserInfo:
        raise NotImplementedError('Telegram WebApp 用户信息解析尚未接入。')


class GenericOAuth3Provider(OAuthProvider):
    """标准 OAuth3 预留实现。"""

    provider_name = 'oauth3'

    def get_authorization_url(self, redirect_uri: str) -> str:
        return f'/auth/oauth/oauth3/authorize/?redirect_uri={redirect_uri}'

    def exchange_token(self, code: str, redirect_uri: str) -> str:
        raise NotImplementedError('OAuth3 token 交换尚未接入，请使用账号密码登录。')

    def get_user_info(self, access_token: str) -> OAuthUserInfo:
        raise NotImplementedError('OAuth3 用户信息解析尚未接入。')


PROVIDERS = {
    'telegram': TelegramWebAppProvider(),
    'oauth3': GenericOAuth3Provider(),
}


def get_provider(name: str) -> OAuthProvider:
    provider = PROVIDERS.get(name)
    if not provider:
        raise ValueError(f'未知 OAuth 提供商: {name}')
    return provider
