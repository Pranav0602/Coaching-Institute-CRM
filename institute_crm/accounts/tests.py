from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import Role, Branch, User
from crm_leads.models import Lead, Admission
from crm_leads.services.lead_service import LeadService
from academics.models import Course, Batch
from finance.models import FeeStructure, Payment, Installment
from finance.services.finance_service import FinanceService

class CRMSystemTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create Roles
        self.role_admin = Role.objects.create(code=Role.SUPER_ADMIN, name='Super Admin')
        self.role_counselor = Role.objects.create(code=Role.ADMISSION_COUNSELOR, name='Counselor')
        self.role_student = Role.objects.create(code=Role.STUDENT, name='Student')
        self.role_teacher = Role.objects.create(code=Role.TEACHER, name='Teacher')

        # Create Branch
        self.branch = Branch.objects.create(
            code='BR-TEST', name='Test Campus', city='Delhi',
            address='123 Street', phone='1234567890', email='test@campus.com'
        )

        # Create Course & Batch
        self.course = Course.objects.create(
            code='CRS-101', title='Test Course', duration_months=12, total_fee=50000.00
        )
        self.batch = Batch.objects.create(
            code='BAT-101', name='Test Batch', course=self.course, branch=self.branch,
            start_date='2026-01-01', end_date='2026-12-31'
        )
        self.fee_struct = FeeStructure.objects.create(
            course=self.course, total_amount=50000.00, deposit_amount=10000.00, num_installments=2
        )

        # Create User
        self.admin_user = User.objects.create_user(
            username='admin_test', email='admin@test.com', password='password123',
            role=self.role_admin, branch=self.branch
        )

    def test_authentication_and_jwt(self):
        res = self.client.post('/api/v1/accounts/auth/login/', {
            'username': 'admin_test',
            'password': 'password123'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_lead_conversion_service(self):
        lead = Lead.objects.create(
            name='John Doe', email='john@example.com', phone='9988776655',
            branch=self.branch, target_course='Test Course', stage='New'
        )
        res = LeadService.convert_lead_to_student(
            lead_id=lead.id,
            course_id=self.course.id,
            batch_id=self.batch.id,
            agreed_fee=48000.00,
            created_by_user=self.admin_user
        )
        self.assertIn('student_user_id', res)
        self.assertEqual(res['username'].startswith('std_john'), True)

        # Verify Lead stage updated to Admitted
        lead.refresh_from_db()
        self.assertEqual(lead.stage, Lead.STAGE_ADMITTED)

        # Verify Installments created
        inst_count = Installment.objects.filter(student_id=res['student_user_id']).count()
        self.assertEqual(inst_count, 2)

    def test_finance_payment_recording(self):
        student = User.objects.create_user(
            username='std_test', email='std@test.com', password='password123',
            role=self.role_student, branch=self.branch
        )
        payment, receipt = FinanceService.record_payment(
            student_user=student,
            amount=25000.00,
            payment_mode='UPI',
            reference_number='UPI-123456',
            recorded_by=self.admin_user
        )
        self.assertEqual(payment.amount, 25000.00)
        self.assertEqual(receipt.receipt_number.startswith('REC-'), True)

    def test_admitted_student_visibility_for_branch_admin_and_teacher(self):
        # 1. Create Branch Admin & Teacher users
        branch_admin_role = Role.objects.create(code=Role.BRANCH_ADMIN, name='Branch Admin')
        branch_admin = User.objects.create_user(
            username='branch_admin_user', email='badmin@test.com', password='password123',
            role=branch_admin_role, branch=self.branch
        )
        teacher_user = User.objects.create_user(
            username='teacher_user', email='teacher@test.com', password='password123',
            role=self.role_teacher, branch=self.branch
        )
        
        # Create a Subject and Timetable for Teacher
        from academics.models import Subject, Timetable
        subject = Subject.objects.create(course=self.course, code='SUB-101', title='Test Subject')
        Timetable.objects.create(
            batch=self.batch, subject=subject, teacher=teacher_user,
            day_of_week='MONDAY', start_time='09:00', end_time='10:30'
        )

        # 2. Admission Counselor admits a lead
        lead = Lead.objects.create(
            name='Alice Smith', email='alice@example.com', phone='9123456789',
            branch=self.branch, target_course='Test Course', stage='New'
        )
        conversion_res = LeadService.convert_lead_to_student(
            lead_id=lead.id,
            course_id=self.course.id,
            batch_id=self.batch.id,
            agreed_fee=45000.00,
            created_by_user=self.admin_user
        )

        # 3. Verify Branch Admin can see the admitted student via API
        self.client.force_authenticate(user=branch_admin)
        res_badmin = self.client.get('/api/v1/profiles/students/')
        self.assertEqual(res_badmin.status_code, 200)
        students_data = res_badmin.data if isinstance(res_badmin.data, list) else res_badmin.data.get('results', [])
        found_alice = any(s['user_detail']['email'] == 'alice@example.com' for s in students_data)
        self.assertTrue(found_alice)

        # 4. Verify Teacher can see the admitted student in their batch section via API
        self.client.force_authenticate(user=teacher_user)
        res_teacher = self.client.get(f'/api/v1/profiles/students/?batch_id={self.batch.id}')
        self.assertEqual(res_teacher.status_code, 200)
        teacher_students_data = res_teacher.data if isinstance(res_teacher.data, list) else res_teacher.data.get('results', [])
        found_alice_teacher = any(s['user_detail']['email'] == 'alice@example.com' for s in teacher_students_data)
        self.assertTrue(found_alice_teacher)
