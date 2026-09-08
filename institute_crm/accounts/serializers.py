"""
Request validation and response shaping for the ``accounts`` app.

Serializers here do exactly two jobs: reject malformed input, and shape output. They do
not create, update, or delete anything - that belongs to ``accounts.services``. This is
why ``UserSerializer`` no longer overrides ``create``/``update``.
"""
from __future__ import annotations

from rest_framework import serializers

from accounts.models import AuditLog, Branch, Role, User


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description']


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'code', 'name', 'city', 'address', 'phone', 'email', 'created_at']
        read_only_fields = ['id', 'created_at']


class BranchStatisticsSerializer(serializers.Serializer):
    """Read-only shape for ``BranchService.branch_statistics``."""

    id = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    city = serializers.CharField(read_only=True)
    total_users = serializers.IntegerField(read_only=True)
    student_count = serializers.IntegerField(read_only=True)
    teacher_count = serializers.IntegerField(read_only=True)


class UserSerializer(serializers.ModelSerializer):
    """Canonical user representation returned by every accounts endpoint."""

    role_name = serializers.CharField(source='role.name', read_only=True)
    role_code = serializers.CharField(source='role.code', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    branch_code = serializers.CharField(source='branch.code', read_only=True)
    full_name = serializers.SerializerMethodField()
    # Resolves uploaded file -> external URL -> null, so the client has one field to read.
    profile_photo_url = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'role_name', 'role_code', 'branch',
            'branch_name', 'branch_code', 'cognito_sub',
            'profile_picture', 'profile_photo_url',
            'is_active', 'date_joined', 'last_login', 'password_changed_at',
            'password',
        ]
        read_only_fields = [
            'id', 'date_joined', 'last_login', 'cognito_sub', 'password_changed_at',
        ]

    def get_full_name(self, obj: User) -> str:
        return obj.get_full_name() or obj.username

    def get_profile_photo_url(self, obj: User) -> str | None:
        url = obj.profile_photo_url
        if not url:
            return None
        # Turn the storage-relative media path into something the browser can fetch
        # directly, since the SPA is served from a different origin in development.
        request = self.context.get('request')
        if request is not None and url.startswith('/'):
            return request.build_absolute_uri(url)
        return url


class UserWriteSerializer(UserSerializer):
    """Input validation for administrative user create/update.

    Splitting write from read keeps the response contract stable while letting the write
    path apply stricter rules.
    """

    class Meta(UserSerializer.Meta):
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True, 'allow_blank': False},
        }

    def validate_email(self, value: str) -> str:
        queryset = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor', 'actor_name', 'action', 'model_name', 'target_id',
            'changes', 'ip_address', 'timestamp',
        ]

    def get_actor_name(self, obj: AuditLog) -> str:
        if obj.actor is None:
            return "System"
        return obj.actor.get_full_name() or obj.actor.username


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="Username or email address.")
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class ForgotPasswordSerializer(serializers.Serializer):
    email_or_username = serializers.CharField()

    def to_internal_value(self, data):
        # Accept the legacy `email` key so existing clients keep working.
        if 'email_or_username' not in data and 'email' in data:
            data = {**data, 'email_or_username': data['email']}
        return super().to_internal_value(data)


class ResetPasswordSerializer(serializers.Serializer):
    email_or_username = serializers.CharField()
    otp = serializers.CharField()
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(
        write_only=True, required=False, style={'input_type': 'password'}
    )

    def to_internal_value(self, data):
        if 'email_or_username' not in data and 'email' in data:
            data = {**data, 'email_or_username': data['email']}
        if 'new_password' not in data and 'password' in data:
            data = {**data, 'new_password': data['password']}
        return super().to_internal_value(data)

    def validate(self, attrs):
        confirm = attrs.get('confirm_password')
        if confirm is not None and attrs['new_password'] != confirm:
            raise serializers.ValidationError(
                {'confirm_password': ["The two passwords do not match."]}
            )
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Shape-only validation for a password change.

    Strength is deliberately *not* checked here - ``AuthService.change_password`` runs
    ``AUTH_PASSWORD_VALIDATORS`` so policy lives in one place and applies to every caller,
    including management commands.
    """

    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(
        write_only=True, style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': ["The two passwords do not match."]}
            )
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {'new_password': ["Please choose a password different from your current one."]}
            )
        return attrs


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Self-service profile edit.

    Only these fields are accepted; role, branch and activation flags are not editable
    here. ``UserService.update_profile`` filters again on its own allow-list, so a bug in
    this serializer cannot become a privilege escalation.
    """

    photo = serializers.ImageField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Optional avatar upload; send as multipart/form-data.",
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'photo']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'email': {'required': False, 'allow_blank': False},
            'phone': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate_email(self, value: str) -> str:
        user = self.instance
        queryset = User.objects.filter(email__iexact=value)
        if user is not None:
            queryset = queryset.exclude(pk=user.pk)
        if queryset.exists():
            raise serializers.ValidationError("This email address is already in use.")
        return value


class ProfilePhotoSerializer(serializers.Serializer):
    """Dedicated avatar upload payload."""

    photo = serializers.ImageField(write_only=True)
