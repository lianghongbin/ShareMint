from django.test import SimpleTestCase

from management.wallet import canonical_bnb_wallet_address, validate_bnb_wallet_address


class BnbWalletValidationTests(SimpleTestCase):
    def test_valid_address_passes(self):
        address = '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0'
        self.assertIsNone(validate_bnb_wallet_address(address))
        self.assertEqual(
            canonical_bnb_wallet_address(address),
            '0x742d35cc6634c0532925a3b844bc9e7595f0beb0',
        )

    def test_empty_address_rejected(self):
        self.assertIsNotNone(validate_bnb_wallet_address(''))

    def test_wrong_length_rejected(self):
        short = '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'
        self.assertIsNotNone(validate_bnb_wallet_address(short))
        self.assertIn('42', validate_bnb_wallet_address(short))

    def test_non_bnb_format_rejected(self):
        self.assertIsNotNone(validate_bnb_wallet_address('TXYZ1234567890'))
        self.assertIsNotNone(validate_bnb_wallet_address('0x1234'))
