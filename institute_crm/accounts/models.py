from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid

from institute_crm.utils import BaseModel


def profile_photo_upload_path(instance, filename: str) -> str:
    """Namespace uploads per user and randomise the stored filename.

    Using the user's UUID keeps files discoverable during support work, while the random
    stem prevents one upload from overwriting another and stops a client-supplied name
    from being used for path traversal.
    """
    extension = (filename.rsplit(".", 1)[-1] if "." in filename else "jpg").lower()
    return f"profile_photos/{instance.pk}/{uuid.uuid4().hex}.{extension}"


class Role(models.Model):
    SUPER_ADMIN = 'SUPER_ADMIN'
    BRANCH_ADMIN = 'BRANCH_ADMIN'
    ADMISSION_COUNSELOR = 'ADMISSION_COUNSELOR'
    TEACHER = 'TEACHER'
    STUDENT = 'STUDENT'
    PARENT = 'PARENT'
    ACCOUNTANT = 'ACCOUNTANT'
    RECEPTIONIST = 'RECEPTIONIST'

    ROLE_CHOICES = [
        (SUPER_ADMIN, 'Super Admin'),
        (BRANCH_ADMIN, 'Branch Admin'),
        (ADMISSION_COUNSELOR, 'Admission Counselor'),
        (TEACHER, 'Teacher'),
        (STUDENT, 'Student'),
        (PARENT, 'Parent'),
        (ACCOUNTANT, 'Accountant'),
        (RECEPTIONIST, 'Receptionist'),
    ]

    #: Roles permitted to administer other users and branch-wide configuration.
    ADMIN_ROLES = (SUPER_ADMIN, BRANCH_ADMIN)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Branch(BaseModel):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Branches'

    def __str__(self):
        return f"{self.name} ({self.code})"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='users', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, related_name='users', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    cognito_sub = models.CharField(max_length=128, blank=True, null=True, unique=True, db_index=True)

    # Two representations of the same concept, deliberately kept separate:
    #   `profile_photo`   - a file this system owns, uploaded through the profile page.
    #   `profile_picture` - an externally hosted URL (S3 mirror, Cognito/social avatar,
    #                       or data seeded before uploads existed).
    # `profile_photo_url` below resolves the two into one value for the API.
    profile_photo = models.ImageField(
        upload_to=profile_photo_upload_path,
        max_length=500,
        blank=True,
        null=True,
        help_text="Uploaded avatar. Takes precedence over profile_picture.",
    )
    profile_picture = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Externally hosted avatar URL (S3 mirror or identity-provider avatar).",
    )

    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful self-service password change; used for audit and "
                  "to prompt rotation of seeded temporary passwords.",
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['first_name', 'last_name', 'username']
        indexes = [
            # Supports the common "active users in my branch with role X" query.
            models.Index(fields=['is_deleted', 'branch', 'role'], name='user_scope_idx'),
        ]

    def __str__(self):
        role_code = self.role.code if self.role else 'NO_ROLE'
        return f"{self.username} ({self.get_full_name() or self.email}) - {role_code}"

    @property
    def role_code(self):
        return self.role.code if self.role else None

    @property
    def profile_photo_url(self) -> str | None:
        """Single avatar URL for the API, preferring the file this system owns.

        Falls back to the external URL, then ``None`` so the frontend can render initials.
        Guarded because a missing file on disk raises on ``.url`` access.
        """
        if self.profile_photo:
            try:
                return self.profile_photo.url
            except ValueError:
                pass
        return self.profile_picture or None

    @property
    def is_admin_role(self) -> bool:
        return self.is_superuser or self.role_code in Role.ADMIN_ROLES

    def mark_password_changed(self, *, commit: bool = True) -> None:
        """Stamp the password rotation time. Call after ``set_password``."""
        self.password_changed_at = timezone.now()
        if commit:
            self.save(update_fields=['password', 'password_changed_at'])


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, db_index=True)  # CREATE, UPDATE, DELETE, LOGIN, ...
    model_name = models.CharField(max_length=100, db_index=True)
    target_id = models.CharField(max_length=128, db_index=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            # "show me the history of this record" - the main forensic query.
            models.Index(fields=['model_name', 'target_id', '-timestamp'],
                         name='auditlog_target_idx'),
        ]

    def __str__(self):
        return f"{self.action} {self.model_name}#{self.target_id} @ {self.timestamp:%Y-%m-%d %H:%M}"
