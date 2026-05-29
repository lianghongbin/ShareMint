import re

BNB_WALLET_LENGTH = 42
BNB_WALLET_PATTERN = re.compile(r'^0x[0-9a-fA-F]{40}$')

BNB_WALLET_REQUIRED_MESSAGE = 'BNB 钱包地址为必填项。'
BNB_WALLET_LENGTH_MESSAGE = (
    'BNB 钱包地址长度错误：BNB Smart Chain 地址固定为 42 位'
    '（0x 开头 + 40 位十六进制）。填错链或填错地址将导致转入资金无法找回。'
)
BNB_WALLET_INVALID_MESSAGE = (
    'BNB 钱包地址格式无效：必须是 BNB Smart Chain（BEP20）链地址，'
    '以 0x 开头，后跟 40 位十六进制字符（共 42 位）。'
    '填错链或填错地址将导致转入资金无法找回。'
)


def normalize_bnb_wallet_address(value: str) -> str:
    return (value or '').strip()


def validate_bnb_wallet_address(value: str) -> str | None:
    """Return an error message if invalid, else None."""
    normalized = normalize_bnb_wallet_address(value)
    if not normalized:
        return BNB_WALLET_REQUIRED_MESSAGE
    if len(normalized) != BNB_WALLET_LENGTH:
        return f'{BNB_WALLET_LENGTH_MESSAGE}（当前 {len(normalized)} 位）'
    if not BNB_WALLET_PATTERN.match(normalized):
        return BNB_WALLET_INVALID_MESSAGE
    return None


def canonical_bnb_wallet_address(value: str) -> str:
    normalized = normalize_bnb_wallet_address(value)
    return normalized.lower()
