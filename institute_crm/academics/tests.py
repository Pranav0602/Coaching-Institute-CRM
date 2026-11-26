from datetime import date

from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import Branch, Role, User
from academics.models import Batch, Course


class BatchVisibilityTests(APITestCase):
    def setUp(self):
        self.branch_admin_role = Role.objects.create(code=Role.BRANCH_ADMIN, name='Branch Admin')
        self.counselor_role = Role.objects.create(code=Role.ADMISSION_COUNSELOR, name='Admission Counselor')
        self.branch_a = Branch.objects.create(code='A', name='Branch A', city='A', address='Address A', phone='1', email='a@example.com')
        self.branch_b = Branch.objects.create(code='B', name='Branch B', city='B', address='Address B', phone='2', email='b@example.com')
        self.course = Course.objects.create(code='FSD', title='Full Stack Development', total_fee=50000)
        self.branch_admin = User.objects.create_user(username='branch-admin', password='password', role=self.branch_admin_role, branch=self.branch_a)
        self.counselor = User.objects.create_user(username='counselor', password='password', role=self.counselor_role, branch=self.branch_a)

    def test_branch_admin_created_batch_is_visible_to_admission_counselor(self):
        self.client.force_authenticate(self.branch_admin)
        create_response = self.client.post(reverse('batch-list'), {
            'course': str(self.course.id),
            'code': 'FSD-A1',
            'name': 'Morning A1',
            'start_date': date(2026, 9, 1),
            'end_date': date(2027, 3, 1),
            'max_capacity': 30,
        }, format='json')

        self.assertEqual(create_response.status_code, 201)
        batch = Batch.objects.get(code='FSD-A1')
        self.assertEqual(batch.branch, self.branch_a)

        Batch.objects.create(course=self.course, branch=self.branch_b, code='FSD-B1', name='Evening B1', start_date=date(2026, 9, 1), end_date=date(2027, 3, 1), max_capacity=30)
        self.client.force_authenticate(self.counselor)
        list_response = self.client.get(reverse('batch-list'))

        self.assertEqual({item['code'] for item in list_response.data}, {'FSD-A1'})

    def test_created_course_is_available_for_batch_creation(self):
        self.client.force_authenticate(self.branch_admin)
        create_response = self.client.post(reverse('course-list'), {
            'code': 'DSA',
            'title': 'Data Structures',
            'duration_months': 6,
            'total_fee': 25000,
            'description': 'Data structures and algorithms.',
        }, format='json')

        self.assertEqual(create_response.status_code, 201)
        courses_response = self.client.get(reverse('course-list'))
        self.assertEqual(courses_response.status_code, 200)
        self.assertIn('DSA', {item['code'] for item in courses_response.data})


class BatchRosterColumnsTests(APITestCase):
    """The batch roster carries the six workbook roster columns."""

    def setUp(self):
        from academics.models import CourseEnrolment
        from users_profiles.models import StudentProfile

        self.branch_admin_role = Role.objects.create(code=Role.BRANCH_ADMIN, name='Branch Admin')
        self.student_role = Role.objects.create(code=Role.STUDENT, name='Student')
        self.branch = Branch.objects.create(code='RC', name='Roster Campus', city='Pune', address='A', phone='1', email='r@example.com')
        self.course = Course.objects.create(code='CAD', title='CAD Mastery', total_fee=50000)
        self.batch = Batch.objects.create(
            code='CAD-R1', name='Roster Batch', course=self.course, branch=self.branch,
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )
        self.admin = User.objects.create_user(
            username='roster-admin', password='password',
            role=self.branch_admin_role, branch=self.branch,
        )
        self.student = User.objects.create_user(
            username='roster-student', password='password',
            role=self.student_role, branch=self.branch, phone='9876543210',
            first_name='Asha', last_name='Patil',
        )
        StudentProfile.objects.create(
            user=self.student, reg_no='REG/RC/2026/1', batch=self.batch,
            secondary_phone='9123456780',
        )
        CourseEnrolment.objects.create(
            student=self.student, course=self.course, batch=self.batch,
            softwares=['AutoCAD', 'SolidWorks'],
        )

    def test_roster_exposes_branch_reg_no_name_mobile_course_softwares(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse('batch-roster', args=[self.batch.pk]))
        self.assertEqual(response.status_code, 200)
        row = response.data[0]
        self.assertEqual(row['branch_name'], 'Roster Campus')
        self.assertEqual(row['reg_no'], 'REG/RC/2026/1')
        self.assertEqual(row['student_name'], 'Asha Patil')
        self.assertEqual(row['phone'], '9876543210')
        self.assertEqual(row['secondary_phone'], '9123456780')
        self.assertEqual(row['course_title'], 'CAD Mastery')
        self.assertEqual(row['softwares'], ['AutoCAD', 'SolidWorks'])
