from django.test import TestCase

from authentication.email_change import apply_user_email_change, validate_new_email
from authentication.models import Role, User
from management.models import Profile


class EmailBindingValidationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='email_owner',
            password='pass12345',
            role=Role.MEMBER,
            email='owner@example.com',
        )
        Profile.objects.create(user=self.owner, name='Owner', email='owner@example.com')
        self.other = User.objects.create_user(
            username='email_other',
            password='pass12345',
            role=Role.MEMBER,
        )
        Profile.objects.create(user=self.other, name='Other', email='')

    def test_rejects_email_already_bound_to_another_account(self):
        error = validate_new_email(self.other, 'owner@example.com')
        self.assertEqual(error, '该邮箱已被其他账号绑定，无法重复绑定。')

    def test_rejects_email_on_profile_only(self):
        profile_only = User.objects.create_user(
            username='profile_only',
            password='pass12345',
            role=Role.MEMBER,
        )
        Profile.objects.create(
            user=profile_only,
            name='Profile Only',
            email='profile-only@example.com',
        )
        error = validate_new_email(self.other, 'profile-only@example.com')
        self.assertEqual(error, '该邮箱已被其他账号绑定，无法重复绑定。')

    def test_apply_user_email_change_rejects_duplicate(self):
        with self.assertRaises(ValueError) as ctx:
            apply_user_email_change(self.other, 'owner@example.com')
        self.assertEqual(str(ctx.exception), '该邮箱已被其他账号绑定，无法重复绑定。')

    def test_allows_binding_unused_email(self):
        self.assertIsNone(validate_new_email(self.other, 'new-user@example.com'))
        apply_user_email_change(self.other, 'new-user@example.com')
        self.other.refresh_from_db()
        self.assertEqual(self.other.email, 'new-user@example.com')
        self.assertEqual(self.other.profile.email, 'new-user@example.com')
