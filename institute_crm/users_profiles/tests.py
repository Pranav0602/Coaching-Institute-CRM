"""Tests for the student roster columns, reg_no rename and computed fee summary."""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from academics.models import Batch, Course, CourseEnrolment
from accounts.models import Branch, Role, User
from finance.models import FeeStructure, Installment, Payment
from users_profiles.models import StudentProfile
from users_profiles.serializers import StudentProfileSerializer


class StudentRosterTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.role_admin = Role.objects.create(code=Role.SUPER_ADMIN, name='Super Admin')
        self.role_student = Role.objects.create(code=Role.STUDENT, name='Student')

        self.branch = Branch.objects.create(
            code='BR-R', name='Roster Campus', city='Pune',
            address='1 Test Road', phone='1234567890', email='roster@campus.com',
        )
        self.course = Course.objects.create(
            code='CRS-R', title='CAD Mastery', duration_months=6, total_fee=100000,
        )
        self.batch = Batch.objects.create(
            code='BAT-R', name='Roster Batch', course=self.course, branch=self.branch,
            start_date='2026-01-01', end_date='2026-12-31',
        )

        self.admin_user = User.objects.create_user(
            username='roster_admin', email='roster_admin@test.com',
            password='password123', role=self.role_admin, branch=self.branch,
        )
        self.student_user = User.objects.create_user(
            username='roster_student', email='roster_student@test.com',
            password='password123', role=self.role_student, branch=self.branch,
            phone='9876543210', first_name='Asha', last_name='Patil',
        )
        self.profile = StudentProfile.objects.create(
            user=self.student_user,
            reg_no='REG/BR-R/2026/0001',
            secondary_phone='9123456780',
            batch=self.batch,
            agreed_fee=Decimal('100000.00'),
            discount_amount=Decimal('5000.00'),
            scholarship_amount=Decimal('10000.00'),
            fee_notes='Approved 10k scholarship by director',
        )
        self.enrolment = CourseEnrolment.objects.create(
            student=self.student_user,
            course=self.course,
            batch=self.batch,
            softwares=['AutoCAD', 'SolidWorks'],
        )

        today = date.today()
        self.fee_structure = FeeStructure.objects.create(
            course=self.course, total_amount=100000, deposit_amount=20000,
            num_installments=2,
        )
        self.installment_one = Installment.objects.create(
            student=self.student_user, fee_structure=self.fee_structure,
            installment_number=1, due_date=today + timedelta(days=10),
            amount=Decimal('40000.00'),
        )
        Installment.objects.create(
            student=self.student_user, fee_structure=self.fee_structure,
            installment_number=2, due_date=today + timedelta(days=40),
            amount=Decimal('40000.00'),
        )
        Payment.objects.create(
            student=self.student_user, installment=self.installment_one,
            amount=Decimal('15000.00'), payment_mode='UPI',
            reference_number='REF-ROSTER-1',
        )

    def test_reg_no_rename_keeps_old_alias_and_qr_lookup(self):
        self.assertEqual(self.profile.reg_no, 'REG/BR-R/2026/0001')
        self.assertEqual(self.profile.enrollment_number, 'REG/BR-R/2026/0001')
        self.assertIn(self.profile.reg_no, self.profile.qr_payload)

        resolved = StudentProfile.from_qr_payload(self.profile.qr_payload)
        self.assertEqual(resolved.pk, self.profile.pk)

    def test_serializer_exposes_both_reg_no_and_compat_alias(self):
        data = StudentProfileSerializer(self.profile).data
        self.assertEqual(data['reg_no'], 'REG/BR-R/2026/0001')
        self.assertEqual(data['enrollment_number'], 'REG/BR-R/2026/0001')

    def test_serializer_exposes_all_six_roster_columns(self):
        data = StudentProfileSerializer(self.profile).data
        self.assertEqual(data['branch_name'], 'Roster Campus')
        self.assertEqual(data['reg_no'], 'REG/BR-R/2026/0001')
        self.assertEqual(data['student_name'], 'Asha Patil')
        self.assertEqual(data['phone'], '9876543210')
        self.assertEqual(data['secondary_phone'], '9123456780')
        self.assertEqual(data['course_title'], 'CAD Mastery')
        self.assertEqual(data['softwares'], ['AutoCAD', 'SolidWorks'])

    def test_serializer_exposes_computed_fee_summary(self):
        data = StudentProfileSerializer(self.profile).data
        self.assertEqual(data['fee_notes'], 'Approved 10k scholarship by director')
        self.assertEqual(data['net_fee'], '85000.00')
        self.assertEqual(data['total_paid'], '15000.00')
        self.assertEqual(data['outstanding_balance'], '65000.00')
        self.assertEqual(data['fee_status'], 'PARTIALLY_PAID')
        self.assertEqual(
            data['next_due_date'],
            (date.today() + timedelta(days=10)).isoformat(),
        )

    def test_api_accepts_legacy_enrollment_number_on_update(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.patch(
            f'/api/v1/profiles/students/{self.profile.pk}/',
            {
                'enrollment_number': 'REG/BR-R/2026/9999',
                'fee_notes': 'Updated concession notes',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.reg_no, 'REG/BR-R/2026/9999')
        self.assertEqual(self.profile.fee_notes, 'Updated concession notes')

    def test_finance_student_summary_endpoint(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(
            '/api/v1/finance/installments/student-summary/',
            {'student_id': str(self.student_user.pk)},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['fee_notes'], 'Approved 10k scholarship by director')
        self.assertEqual(res.data['net_fee'], '85000.00')
        self.assertEqual(res.data['total_paid'], '15000.00')
        self.assertEqual(res.data['outstanding_balance'], '65000.00')
        self.assertEqual(res.data['fee_status'], 'PARTIALLY_PAID')
