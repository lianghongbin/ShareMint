from rest_framework import serializers

from authentication.models import Role, User
from authentication.password_history import REUSED_PASSWORD_MESSAGE, change_user_password, is_password_reused
from management.models import Investment, Profile


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'role',
            'role_display',
            'is_first_login',
            'two_factor_enabled',
            'two_factor_method',
            'two_factor_totp_enabled',
            'two_factor_email_enabled',
            'referrer',
        )
        read_only_fields = (
            'id',
            'is_first_login',
            'two_factor_enabled',
            'two_factor_method',
            'two_factor_totp_enabled',
            'two_factor_email_enabled',
        )


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('id', 'name', 'phone', 'wechat', 'email')
        read_only_fields = ('id', 'email')

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and user.role == Role.MEMBER:
            fields['name'].read_only = True
        return fields


class InvestmentSerializer(serializers.ModelSerializer):
    current_market_value = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        read_only=True,
    )

    class Meta:
        model = Investment
        fields = (
            'id',
            'user',
            'investment_date',
            'investment_amount',
            'holding_quantity',
            'holding_currency',
            'current_market_value',
        )
        read_only_fields = ('id',)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': '两次输入的新密码不一致。'})
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('原密码不正确。')
        return value

    def validate_new_password(self, value):
        user = self.context['request'].user
        if is_password_reused(user, value):
            raise serializers.ValidationError(REUSED_PASSWORD_MESSAGE)
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        change_user_password(user, self.validated_data['new_password'])
        return user
