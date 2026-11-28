"""Branch filtering + multi-tenant scoping for students and staff."""
from datetime import date

from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import Branch, Role, User
from users_profiles.models import StudentProfile, TeacherProfile


def branch(code):
    return Branch.objects.create(code=code, name=f'Branch {code}', city='X', address='A', phone='1', email=f'{code}@x.com')


class BranchFilterTests(APITestCase):
    def setUp(self):
        self.super_role = Role.objects.get_or_create(code=Role.SUPER_ADMIN, defaults={'name': 'Super Admin'})[0]
        self.admin_role = Role.objects.get_or_create(code=Role.BRANCH_ADMIN, defaults={'name': 'Branch Admin'})[0]
        self.teacher_role = Role.objects.get_or_create(code=Role.TEACHER, defaults={'name': 'Teacher'})[0]
        self.student_role = Role.objects.get_or_create(code=Role.STUDENT, defaults={'name': 'Student'})[0]
        self.reception_role = Role.objects.get_or_create(code=Role.RECEPTIONIST, defaults={'name': 'Receptionist'})[0]

        self.branch_a = branch('A')
        self.branch_b = branch('B')
        self.branch_c = branch('C')

        self.super_admin = User.objects.create_user(username='super', password='pw', role=self.super_role)
        self.admin_a = User.objects.create_user(username='admin_a', password='pw', role=self.admin_role, branch=self.branch_a)
        self.reception_a = User.objects.create_user(username='rec_a', password='pw', role=self.reception_role, branch=self.branch_a)

        # students across branches
        self.s_a = self._student('sa', self.branch_a, 'RA')
        self.s_b = self._student('sb', self.branch_b, 'RB')
        self.s_c = self._student('sc', self.branch_c, 'RC')

        # teachers across branches
        self.t_a = self._teacher('ta', self.branch_a, 'EA')
        self.t_b = self._teacher('tb', self.branch_b, 'EB')

    def _student(self, username, branch, reg):
        user = User.objects.create_user(username=username, password='pw', role=self.student_role, branch=branch, first_name=username, last_name='X')
        StudentProfile.objects.create(user=user, reg_no=reg)
        return user

    def _teacher(self, username, branch, emp):
        user = User.objects.create_user(username=username, password='pw', role=self.teacher_role, branch=branch, first_name=username, last_name='X')
        TeacherProfile.objects.create(user=user, employee_id=emp)
        return user

    def _names(self, res, key='data'):
        body = res.data
        data = body.get(key, body) if isinstance(body, dict) else body
        return {row.get('user_detail', {}).get('username') for row in data}

    # ---------------------------------------------------------- super admin

    def test_super_admin_students_all_branches_default(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.get(reverse('student-profile-list'))
        self.assertEqual(res.status_code, 200)
        names = {row['user_detail']['username'] for row in (res.data['data'] if isinstance(res.data, dict) else res.data)}
        self.assertTrue({'sa', 'sb', 'sc'} <= names)

    def test_super_admin_student_filter_single_branch(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.get(reverse('student-profile-list'), {'branch_id': str(self.branch_a.pk)})
        names = {row['user_detail']['username'] for row in (res.data['data'] if isinstance(res.data, dict) else res.data)}
        self.assertEqual(names, {'sa'})

    def test_super_admin_student_filter_multi_branch(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.get(reverse('student-profile-list'), {'branch_ids': [str(self.branch_a.pk), str(self.branch_b.pk)]})
        names = {row['user_detail']['username'] for row in (res.data['data'] if isinstance(res.data, dict) else res.data)}
        self.assertEqual(names, {'sa', 'sb'})

    def test_super_admin_student_search_respects_branch(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.get(reverse('student-profile-list'), {'branch_id': str(self.branch_b.pk), 'search': 's'})
        names = {row['user_detail']['username'] for row in (res.data['data'] if isinstance(res.data, dict) else res.data)}
        self.assertNotIn('sa', names)

    def test_super_admin_users_branch_filter(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.get(reverse('user-list'), {'branch_id': str(self.branch_b.pk)})
        names = {u['username'] for u in (res.data['data'] if isinstance(res.data, dict) else res.data)}
        self.assertIn('sb', names)
        self.assertNotIn('sa', names)

    def test_super_admin_users_multi_branch_filter(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.get(reverse('user-list'), {'branch_ids': [str(self.branch_a.pk), str(self.branch_c.pk)]})
        names = {u['username'] for u in (res.data['data'] if isinstance(res.data, dict) else res.data)}
        self.assertIn('sa', names)
        self.assertIn('sc', names)
        self.assertNotIn('sb', names)

    def test_super_admin_teachers_branch_filter(self):
        self.client.force_authenticate(self.super_admin)
        res = self.client.get(reverse('teacher-profile-list'), {'branch_id': str(self.branch_a.pk)})
        body = res.data['data'] if isinstance(res.data, dict) else res.data
        names = {row['user_detail']['username'] for row in body}
        self.assertEqual(names, {'ta'})

    # ------------------------------------------------------- other roles

    def test_branch_admin_cannot_escape_own_branch_via_filter(self):
        self.client.force_authenticate(self.admin_a)
        # tries to filter to another branch
        res = self.client.get(reverse('student-profile-list'), {'branch_id': str(self.branch_b.pk)})
        names = {row['user_detail']['username'] for row in (res.data['data'] if isinstance(res.data, dict) else res.data)}
        self.assertNotIn('sb', names)
        self.assertNotIn('sc', names)
        self.assertEqual(names, set())

    def test_receptionist_cannot_escape_own_branch(self):
        self.client.force_authenticate(self.reception_a)
        res = self.client.get(reverse('student-profile-list'), {'branch_id': str(self.branch_b.pk)})
        names = {row['user_detail']['username'] for row in (res.data['data'] if isinstance(res.data, dict) else res.data)}
        self.assertNotIn('sb', names)

    def test_branch_admin_users_scoped(self):
        self.client.force_authenticate(self.admin_a)
        res = self.client.get(reverse('user-list'), {'branch_id': str(self.branch_b.pk)})
        names = {u['username'] for u in (res.data['data'] if isinstance(res.data, dict) else res.data)}
        self.assertNotIn('sb', names)

    def test_url_tampering_cannot_leak_other_branch(self):
        self.client.force_authenticate(self.admin_a)
        # attempt to read another branch's student directly
        res = self.client.get(reverse('student-profile-detail', args=['RB']))
        self.assertIn(res.status_code, (404, 403))
