"""Super Admin -> User Access & Roles filters: name/email/reg_no/course/batch/branch; combined; scoped."""
from datetime import date

from django.urls import reverse
from rest_framework.test import APITestCase

from academics.models import Batch, Course, CourseEnrolment
from accounts.models import Branch, Role, User
from users_profiles.models import StudentProfile


def branch(code):
    return Branch.objects.create(code=code, name=f'Branch {code}', city='X', address='A', phone='1', email=f'{code}@x.com')


class UserAccessFiltersTests(APITestCase):
    def setUp(self):
        self.super_role = Role.objects.get_or_create(code=Role.SUPER_ADMIN, defaults={'name': 'Super Admin'})[0]
        self.student_role = Role.objects.get_or_create(code=Role.STUDENT, defaults={'name': 'Student'})[0]
        self.admin_role = Role.objects.get_or_create(code=Role.BRANCH_ADMIN, defaults={'name': 'Branch Admin'})[0]
        self.branch_a = branch('A')
        self.branch_b = branch('B')
        self.course = Course.objects.create(code='C', title='Course', total_fee=100)
        self.batch = Batch.objects.create(course=self.course, branch=self.branch_a, code='BA', name='BA', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))
        self.super_admin = User.objects.create_user(username='super', password='pw', role=self.super_role)

        self.alice = User.objects.create_user(username='alice', password='pw', role=self.student_role, branch=self.branch_a, first_name='Alice', last_name='Smith', email='alice@x.com')
        self.bob = User.objects.create_user(username='bob', password='pw', role=self.student_role, branch=self.branch_b, first_name='Bob', last_name='Jones', email='bob@y.com')
        StudentProfile.objects.create(user=self.alice, reg_no='REG/A/1', batch=self.batch, course=self.course)
        StudentProfile.objects.create(user=self.bob, reg_no='REG/B/2')
        CourseEnrolment.objects.create(student=self.alice, course=self.course, batch=self.batch, status='ACTIVE')
        self.client.force_authenticate(self.super_admin)

    def _names(self, **params):
        res = self.client.get(reverse('user-list'), params)
        self.assertEqual(res.status_code, 200, res.data)
        body = res.data['data'] if isinstance(res.data, dict) and 'data' in res.data else res.data
        if isinstance(body, dict) and 'results' in body:
            body = body['results']
        return {u['username'] for u in body}

    def test_filter_name(self):
        self.assertEqual(self._names(name='ali'), {'alice'})
        self.assertEqual(self._names(name='smith'), {'alice'})

    def test_filter_email(self):
        self.assertEqual(self._names(email='alice@x.com'), {'alice'})

    def test_filter_registration_number(self):
        self.assertEqual(self._names(reg_no='REG/A/1'), {'alice'})
        self.assertEqual(self._names(reg_no='REG/B'), {'bob'})

    def test_filter_course(self):
        self.assertEqual(self._names(course_id=str(self.course.pk)), {'alice'})

    def test_filter_batch(self):
        self.assertEqual(self._names(batch_id=str(self.batch.pk)), {'alice'})

    def test_filter_branch(self):
        names = self._names(branch_id=str(self.branch_b.pk))
        self.assertIn('bob', names)
        self.assertNotIn('alice', names)

    def test_combined_filters(self):
        self.assertEqual(self._names(name='a', email='x.com', reg_no='REG', course_id=str(self.course.pk), batch_id=str(self.batch.pk), branch_id=str(self.branch_a.pk)), {'alice'})

    def test_clear_returns_all(self):
        self.assertTrue({'alice', 'bob'} <= self._names())
