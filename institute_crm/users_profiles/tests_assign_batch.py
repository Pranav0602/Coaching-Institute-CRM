"""Assign a valid batch to an unassigned student; server validation."""
from datetime import date

from django.urls import reverse
from rest_framework.test import APITestCase

from academics.models import Batch, Course, CourseEnrolment
from accounts.models import Branch, Role, User
from users_profiles.models import StudentProfile


def branch(code):
    return Branch.objects.create(code=code, name=f'Branch {code}', city='X', address='A', phone='1', email=f'{code}@x.com')


class AssignBatchTests(APITestCase):
    def setUp(self):
        self.reception_role = Role.objects.get_or_create(code=Role.RECEPTIONIST, defaults={'name': 'Receptionist'})[0]
        self.student_role = Role.objects.get_or_create(code=Role.STUDENT, defaults={'name': 'Student'})[0]
        self.teacher_role = Role.objects.get_or_create(code=Role.TEACHER, defaults={'name': 'Teacher'})[0]
        self.branch = branch('A')
        self.other = branch('B')
        self.course = Course.objects.create(code='C', title='Course', total_fee=100)
        self.other_course = Course.objects.create(code='D', title='Other', total_fee=100)
        self.batch = Batch.objects.create(course=self.course, branch=self.branch, code='BA', name='BA', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1), max_capacity=40)
        self.batch_other_course = Batch.objects.create(course=self.other_course, branch=self.branch, code='BD', name='BD', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))
        self.batch_other_branch = Batch.objects.create(course=self.course, branch=self.other, code='BB', name='BB', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))
        self.reception = User.objects.create_user(username='rec', password='pw', role=self.reception_role, branch=self.branch)
        self.student_user = User.objects.create_user(username='s', password='pw', role=self.student_role, branch=self.branch)
        self.profile = StudentProfile.objects.create(user=self.student_user, reg_no='R1', course=self.course)

    def _assign(self, batch, actor=None):
        self.client.force_authenticate(actor or self.reception)
        return self.client.post(
            reverse('student-profile-assign-batch', args=[self.profile.pk]),
            {'batch': str(batch.pk) if hasattr(batch, 'pk') else batch}, format='json',
        )

    def test_assign_valid_batch_to_unassigned_student(self):
        self.assertIsNone(self.profile.batch_id)
        res = self._assign(self.batch)
        self.assertEqual(res.status_code, 200, res.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.batch_id, self.batch.pk)
        self.assertTrue(CourseEnrolment.objects.filter(student=self.student_user, batch=self.batch, status='ACTIVE').exists())

    def test_reject_cross_branch_batch(self):
        res = self._assign(self.batch_other_branch)
        self.assertEqual(res.status_code, 400, res.data)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.batch_id)

    def test_reject_course_mismatch(self):
        res = self._assign(self.batch_other_course)
        self.assertEqual(res.status_code, 400, res.data)

    def test_reject_invalid_batch(self):
        res = self._assign('00000000-0000-0000-0000-000000000000')
        self.assertEqual(res.status_code, 400)

    def test_prevent_duplicate_assignment(self):
        res1 = self._assign(self.batch)
        self.assertEqual(res1.status_code, 200, res1.data)
        res2 = self._assign(self.batch)
        self.assertEqual(res2.status_code, 409, res2.data)
        self.assertEqual(CourseEnrolment.objects.filter(student=self.student_user, batch=self.batch).count(), 1)

    def test_unauthorized_cannot_assign(self):
        teacher = User.objects.create_user(username='t', password='pw', role=self.teacher_role, branch=self.branch)
        res = self._assign(self.batch, actor=teacher)
        self.assertEqual(res.status_code, 403)

    def test_student_with_no_course_can_assign_any_branch_course(self):
        self.profile.course = None
        self.profile.save(update_fields=['course'])
        res = self._assign(self.batch_other_course)
        self.assertEqual(res.status_code, 200, res.data)
