from django.db import models
import uuid
from institute_crm.utils import BaseModel
from accounts.models import User

class StudentProfile(BaseModel):
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    #: Registration number (workbook heading "REG NO"). Renamed from `enrollment_number`;
    #: the old name is kept as a compatibility alias (see `enrollment_number` below).
    reg_no = models.CharField(max_length=50, unique=True, db_index=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='MALE')
    blood_group = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    #: Second mobile number, stored as its own string - never a numeric field and
    #: never a comma-joined value inside `user.phone`. Blank when there is only one.
    secondary_phone = models.CharField(max_length=20, blank=True, null=True)
    batch = models.ForeignKey('academics.Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    documents_url = models.JSONField(default=list, blank=True) # AWS S3 stored document URLs

    # ------------------------------------------------------------- fee terms
    # Student-specific fee terms, in Indian Rupees (INR). These are *terms*, not
    # transaction history: installments, payments, receipts and refunds stay in
    # `finance`. Net fee / total paid / outstanding balance / next due date /
    # fee status are computed live from these terms + finance records (see
    # `finance.services.finance_service.FinanceService.student_fee_summary`)
    # and are read-only; they are never stored as independently editable data.
    agreed_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    concession_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    scholarship_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __init__(self, *args, **kwargs):
        # Backwards compatibility: accept the old `enrollment_number` kwarg.
        if 'enrollment_number' in kwargs and 'reg_no' not in kwargs:
            kwargs['reg_no'] = kwargs.pop('enrollment_number')
        super().__init__(*args, **kwargs)

    #: Deep-link scheme the mobile app registers for check-in scanning.
    QR_SCHEME = 'graphix://student/'

    @property
    def enrollment_number(self) -> str:
        """Backwards-compatible alias for :attr:`reg_no`."""
        return self.reg_no

    @enrollment_number.setter
    def enrollment_number(self, value) -> None:
        self.reg_no = value

    @property
    def qr_payload(self) -> str:
        """Stable identifier encoded in the student's ID card.

        Keyed on the registration number (REG NO) rather than the primary key:
        reg numbers are printed on ID cards and are what reception staff read out
        over the counter, so the code has to survive a re-import of the user table.
        """
        return f'{self.QR_SCHEME}{self.reg_no}'

    @classmethod
    def from_qr_payload(cls, payload: str) -> 'StudentProfile | None':
        """Resolve a scanned payload back to a profile, or ``None`` if foreign.

        The payload carries the reg number; matching is case-insensitive. Cards
        printed before the `enrollment_number` -> `reg_no` rename keep working
        because the printed value itself is unchanged.
        """
        prefix = cls.QR_SCHEME
        if not payload or not payload.startswith(prefix):
            return None
        reg_no = payload[len(prefix):].strip()
        if not reg_no:
            return None
        return cls.objects.filter(
            reg_no__iexact=reg_no,
            is_deleted=False,
        ).select_related(
            'user', 'user__branch', 'batch', 'batch__course', 'batch__branch'
        ).prefetch_related('user__enrolments__course').first()

    def __str__(self):
        return f"StudentProfile: {self.user.get_full_name()} ({self.reg_no})"


class TeacherProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    employee_id = models.CharField(max_length=50, unique=True, db_index=True)
    qualification = models.CharField(max_length=200, blank=True, null=True)
    specialization = models.CharField(max_length=200, blank=True, null=True)
    joining_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"TeacherProfile: {self.user.get_full_name()} ({self.employee_id})"


class ParentProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    occupation = models.CharField(max_length=100, blank=True, null=True)
    relationship_type = models.CharField(max_length=50, default='FATHER') # FATHER, MOTHER, GUARDIAN

    def __str__(self):
        return f"ParentProfile: {self.user.get_full_name()}"


class StudentParent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='parent_links')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='student_links')
    is_primary = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'parent')

    def __str__(self):
        return f"{self.student.user.username} <-> {self.parent.user.username}"
