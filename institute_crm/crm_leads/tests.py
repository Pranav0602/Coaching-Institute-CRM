from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import Role, Branch, User
from academics.models import Course, Batch
from crm_leads.models import Lead


class LeadPipelineAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_counselor = Role.objects.create(code=Role.ADMISSION_COUNSELOR, name='Counselor')
        self.role_super_admin = Role.objects.create(code=Role.SUPER_ADMIN, name='Super Admin')

        self.branch_a = Branch.objects.create(
            code='BR-A', name='Campus A', city='Delhi',
            address='123 Street', phone='1234567890', email='a@campus.com'
        )
        self.branch_b = Branch.objects.create(
            code='BR-B', name='Campus B', city='Mumbai',
            address='456 Street', phone='0987654321', email='b@campus.com'
        )

        self.course = Course.objects.create(
            code='CRS-101', title='Test Course', duration_months=12, total_fee=50000.00
        )
        self.batch_a = Batch.objects.create(
            code='BAT-A', name='Batch A', course=self.course, branch=self.branch_a,
            start_date='2026-01-01', end_date='2026-12-31'
        )
        self.batch_b = Batch.objects.create(
            code='BAT-B', name='Batch B', course=self.course, branch=self.branch_b,
            start_date='2026-01-01', end_date='2026-12-31'
        )

        self.counselor = User.objects.create_user(
            username='counselor_test', email='counselor@test.com', password='password123',
            role=self.role_counselor, branch=self.branch_a
        )
        self.admin = User.objects.create_user(
            username='admin_test', email='admin@test.com', password='password123',
            role=self.role_super_admin, branch=self.branch_a
        )

        self.lead_owned = Lead.objects.create(
            name='Owned Lead', email='owned@test.com', phone='1111111111',
            branch=self.branch_a, course=self.course, stage='New', lead_owner=self.counselor
        )
        self.lead_other = Lead.objects.create(
            name='Other Lead', email='other@test.com', phone='2222222222',
            branch=self.branch_b, course=self.course, stage='Contacted', lead_owner=self.admin
        )
        self.lead_unassigned = Lead.objects.create(
            name='Unassigned Lead', email='unassigned@test.com', phone='3333333333',
            branch=self.branch_b, stage='New', lead_owner=None
        )

    @staticmethod
    def as_list(res):
        data = res.data
        return data if isinstance(data, list) else data.get('results', [])

    def test_stage_counts_endpoint(self):
        self.client.force_authenticate(user=self.counselor)
        res = self.client.get('/api/v1/crm/leads/stage-counts/')
        self.assertEqual(res.status_code, 200)
        # Counselor sees own lead + unassigned leads only
        self.assertEqual(res.data.get('New'), 2)
        self.assertIsNone(res.data.get('Contacted'))

    def test_stage_counts_scoping_for_super_admin(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/crm/leads/stage-counts/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data.get('New'), 2)
        self.assertEqual(res.data.get('Contacted'), 1)

    def test_stage_filter_still_works(self):
        self.client.force_authenticate(user=self.counselor)
        res = self.client.get('/api/v1/crm/leads/?stage=New')
        self.assertEqual(res.status_code, 200)
        results = self.as_list(res)
        self.assertEqual(len(results), 2)

    def test_branch_filter_still_works(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f'/api/v1/crm/leads/?branch_id={self.branch_b.id}')
        self.assertEqual(res.status_code, 200)
        results = self.as_list(res)
        self.assertEqual(len(results), 2)

    def test_course_filter(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f'/api/v1/crm/leads/?course_id={self.course.id}')
        self.assertEqual(res.status_code, 200)
        results = self.as_list(res)
        self.assertEqual(len(results), 2)

    def test_lead_serializer_exposes_course_batch_branch(self):
        self.lead_owned.course = self.course
        self.lead_owned.batch = self.batch_a
        self.lead_owned.save(update_fields=['course', 'batch'])
        self.client.force_authenticate(user=self.counselor)
        res = self.client.get('/api/v1/crm/leads/')
        results = self.as_list(res)
        lead_data = next(l for l in results if l['id'] == str(self.lead_owned.id))
        self.assertEqual(lead_data['course_title'], 'Test Course')
        self.assertEqual(lead_data['course_code'], 'CRS-101')
        self.assertEqual(lead_data['batch_name'], 'Batch A')
        self.assertEqual(lead_data['batch_code'], 'BAT-A')
        self.assertEqual(lead_data['branch_name'], 'Campus A')

    def test_assign_batch_via_patch(self):
        self.client.force_authenticate(user=self.counselor)
        res = self.client.patch(
            f'/api/v1/crm/leads/{self.lead_owned.id}/',
            {'batch': str(self.batch_a.id), 'course': str(self.course.id)},
            format='json'
        )
        self.assertEqual(res.status_code, 200)
        self.lead_owned.refresh_from_db()
        self.assertEqual(self.lead_owned.batch, self.batch_a)
        self.assertEqual(self.lead_owned.course, self.course)
        self.assertEqual(res.data['batch_name'], 'Batch A')