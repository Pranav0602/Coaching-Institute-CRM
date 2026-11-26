from rest_framework import serializers
from users_profiles.models import StudentProfile, TeacherProfile, ParentProfile, StudentParent
from accounts.serializers import UserSerializer

class StudentProfileSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)
    qr_payload = serializers.CharField(read_only=True)

    # Backwards-compatible alias for `reg_no` (old clients read `enrollment_number`).
    enrollment_number = serializers.CharField(source='reg_no', required=False)

    # ---- roster columns (workbook headings) -------------------------------
    # BRANCH, REG NO, STUDENT NAME, MOB.NO, COURSE, SOFTWARES. Reuses existing
    # relationships: name/phone from the linked user, branch from user/batch,
    # course from course enrolment; softwares from the course enrolment(s).
    branch_name = serializers.SerializerMethodField()
    branch_code = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    mobile = serializers.SerializerMethodField()  # MOB.NO alias for `phone`
    course_title = serializers.SerializerMethodField()
    course_code = serializers.SerializerMethodField()
    batch_code = serializers.CharField(source='batch.code', read_only=True)
    softwares = serializers.SerializerMethodField()
    guardian = serializers.SerializerMethodField()

    # ---- student-specific fee terms (INR) ---------------------------------
    # Computed, read-only summary; underlying records stay in `finance`.
    net_fee = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    outstanding_balance = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()
    fee_status = serializers.SerializerMethodField()
    fee_summary = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user', 'user_detail', 'reg_no', 'enrollment_number', 'dob',
            'gender', 'blood_group', 'address', 'emergency_contact',
            'secondary_phone', 'course', 'course_code', 'academic_branch',
            'source_course_label', 'source_softwares', 'batch', 'batch_name',
            'batch_code', 'documents_url', 'qr_payload',
            'guardian_name', 'guardian_phone', 'guardian_relationship', 'guardian',
            'branch_name', 'branch_code', 'student_name', 'phone', 'mobile',
            'course_title', 'softwares',
            'agreed_fee', 'discount_amount', 'concession_amount', 'scholarship_amount',
            'fee_notes',
            'net_fee', 'total_paid', 'outstanding_balance', 'next_due_date',
            'fee_status', 'fee_summary', 'created_at'
        ]

    # -- compatibility: accept `enrollment_number` as input alias for `reg_no`
    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        if 'reg_no' not in data and 'enrollment_number' in data:
            data['reg_no'] = data.pop('enrollment_number')
        return super().to_internal_value(data)

    # -- roster helpers ------------------------------------------------------
    def _branch(self, obj):
        user_branch = getattr(obj.user, 'branch', None)
        if user_branch is not None:
            return user_branch
        if obj.batch is not None:
            return getattr(obj.batch, 'branch', None)
        return None

    def get_branch_name(self, obj):
        branch = self._branch(obj)
        return getattr(branch, 'name', None)

    def get_branch_code(self, obj):
        branch = self._branch(obj)
        return getattr(branch, 'code', None)

    def get_student_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_phone(self, obj):
        return obj.user.phone

    def get_mobile(self, obj):
        return obj.user.phone

    def _enrolments(self, obj):
        try:
            # `.all()` uses the prefetch cache when the queryset prefetched
            # `user__enrolments__course`; otherwise it is a single extra query.
            return [e for e in obj.user.enrolments.all() if not e.is_deleted]
        except Exception:
            return []

    def _course(self, obj):
        enrolments = self._enrolments(obj)
        if enrolments:
            return getattr(enrolments[0], 'course', None)
        if obj.batch is not None and getattr(obj.batch, 'course', None) is not None:
            return obj.batch.course
        return getattr(obj, 'course', None)

    def get_course_title(self, obj):
        return getattr(self._course(obj), 'title', None) or obj.source_course_label

    def get_course_code(self, obj):
        return getattr(self._course(obj), 'code', None)

    def get_guardian(self, obj):
        """Single guardian block for the profile viewer, with legacy fallbacks."""
        return {
            'name': obj.guardian_name or None,
            'phone': obj.guardian_phone or obj.emergency_contact or None,
            'relationship': obj.guardian_relationship or None,
        }

    def get_softwares(self, obj):
        softwares: list = []
        for enrolment in self._enrolments(obj):
            for software in (enrolment.softwares or []):
                if software not in softwares:
                    softwares.append(software)
        if not softwares and obj.source_softwares:
            # Preserve a useful roster list while exposing the untouched source
            # cell separately for audit and exact round-tripping.
            import re
            softwares = [
                value.strip()
                for value in re.split(r'\s*[+;]\s*', obj.source_softwares)
                if value.strip()
            ]
        return softwares

    # -- fee helpers ---------------------------------------------------------
    def _fee_summary(self, obj):
        cached = getattr(obj, '_fee_summary_cache', None)
        if cached is None:
            from finance.services.finance_service import FinanceService

            cached = FinanceService.student_fee_summary(obj.user)
            obj._fee_summary_cache = cached
        return cached

    def get_net_fee(self, obj):
        return self._fee_summary(obj)['net_fee']

    def get_total_paid(self, obj):
        return self._fee_summary(obj)['total_paid']

    def get_outstanding_balance(self, obj):
        return self._fee_summary(obj)['outstanding_balance']

    def get_next_due_date(self, obj):
        return self._fee_summary(obj)['next_due_date']

    def get_fee_status(self, obj):
        return self._fee_summary(obj)['fee_status']

    def get_fee_summary(self, obj):
        return self._fee_summary(obj)


class TeacherProfileSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = TeacherProfile
        fields = ['id', 'user', 'user_detail', 'employee_id', 'qualification', 'specialization', 'joining_date']


class ParentProfileSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = ParentProfile
        fields = ['id', 'user', 'user_detail', 'occupation', 'relationship_type']
