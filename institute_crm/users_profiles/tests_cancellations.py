"""Student admission cancellation + removal of cancelled-admission records."""
from datetime import date

from django.urls import reverse
from rest_framework.test import APITestCase

from academics.models import Batch, Course, CourseEnrolment
from accounts.models import AuditLog, Branch, Role, User
from users_profiles.models import StudentProfile
from users_profiles.services.profile_service import ProfileService


def make_branch(code):
    return Branch.objects.create(code=code, name=f'Branch {code}', city='X', address='A', phone='1', email=f'{code}@x.com')


class AdmissionCancellationTests(APITestCase):
    def setUp(self):
        self.receptionist_role = Role.objects.get_or_create(code=Role.RECEPTIONIST, defaults={'name': 'Receptionist'})[0]
        self.student_role = Role.objects.get_or_create(code=Role.STUDENT, defaults={'name': 'Student'})[0]
        self.teacher_role = Role.objects.get_or_create(code=Role.TEACHER, defaults={'name': 'Teacher'})[0]
        self.branch = make_branch('A')
        self.other_branch = make_branch('B')
        self.course = Course.objects.create(code='C', title='Course', total_fee=100)
        self.batch = Batch.objects.create(
            course=self.course, branch=self.branch, code='B1', name='B1',
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 1),
        )

        self.reception = User.objects.create_user(
            username='reception', password='pw', role=self.receptionist_role, branch=self.branch,
        )
        self.other_branch_reception = User.objects.create_user(
            username='reception_b', password='pw', role=self.receptionist_role, branch=self.other_branch,
        )
        self.teacher = User.objects.create_user(
            username='teacher', password='pw', role=self.teacher_role, branch=self.branch,
        )

    def _student(self, username, *, branch=None, reg='R1', enrol=False, batch=None):
        user = User.objects.create_user(
            username=username, password='pw', role=self.student_role, branch=branch or self.branch,
            first_name=username.title(), last_name='X',
        )
        profile = StudentProfile.objects.create(user=user, reg_no=reg, batch=batch)
        if enrol:
            CourseEnrolment.objects.create(student=user, course=self.course, batch=batch or self.batch, status='ACTIVE')
        return user, profile

    def test_reception_can_cancel_admission(self):
        _, profile = self._student('s1', reg='R-C1')
        self.client.force_authenticate(self.reception)
        res = self.client.post(
            reverse('student-profile-cancel-admission', args=[profile.pk]),
            {'reason': 'Student withdrew'}, format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        profile.refresh_from_db()
        self.assertEqual(profile.admission_status, StudentProfile.ADMISSION_CANCELLED)
        self.assertEqual(profile.cancellation_reason, 'Student withdrew')
        self.assertTrue(AuditLog.objects.filter(model_name='StudentProfile', target_id=profile.pk).exists())

    def test_teacher_cannot_cancel_admission(self):
        _, profile = self._student('s2', reg='R-C2')
        self.client.force_authenticate(self.teacher)
        res = self.client.post(reverse('student-profile-cancel-admission', args=[profile.pk]), {}, format='json')
        self.assertEqual(res.status_code, 403)
        profile.refresh_from_db()
        self.assertEqual(profile.admission_status, StudentProfile.ADMISSION_PENDING)

    def test_cannot_cancel_enrolled_student(self):
        _, profile = self._student('s3', reg='R-C3', enrol=True)
        self.client.force_authenticate(self.reception)
        res = self.client.post(reverse('student-profile-cancel-admission', args=[profile.pk]), {}, format='json')
        self.assertEqual(res.status_code, 409)

    # ----------------------------------------------------------- deletion

    def _cancelled(self, username, reg, **kw):
        user, profile = self._student(username, reg=reg, **kw)
        profile.admission_status = StudentProfile.ADMISSION_CANCELLED
        profile.save(update_fields=['admission_status'])
        return user, profile

    def test_reception_can_delete_cancelled_admission(self):
        _, profile = self._cancelled('c1', 'R-D1')
        self.client.force_authenticate(self.reception)
        res = self.client.delete(
            reverse('student-profile-detail', args=[profile.pk]),
            {'confirm': True, 'reason': 'Admission cancelled - cleanup'}, format='json',
        )
        self.assertEqual(res.status_code, 204, getattr(res, 'data', None))
        profile.refresh_from_db()
        self.assertTrue(profile.is_deleted)
        self.assertIsNotNone(profile.deleted_at)
        self.assertEqual(profile.deletion_reason, 'Admission cancelled - cleanup')
        # removed from active views
        self.assertFalse(StudentProfile.objects.filter(pk=profile.pk, is_deleted=False).exists())
        # history retained + audit written
        self.assertTrue(StudentProfile.objects.filter(pk=profile.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action='DELETE', model_name='StudentProfile', target_id=profile.pk).exists())
        # no longer in directory
        list_res = self.client.get(reverse('student-profile-list'))
        body = list_res.data
        rows = body['data'] if isinstance(body, dict) and 'data' in body else body
        ids = [row['reg_no'] for row in rows]
        self.assertNotIn(profile.pk, ids)

    def test_delete_requires_confirmation(self):
        _, profile = self._cancelled('c2', 'R-D2')
        self.client.force_authenticate(self.reception)
        res = self.client.delete(reverse('student-profile-detail', args=[profile.pk]), {}, format='json')
        self.assertEqual(res.status_code, 400)
        profile.refresh_from_db()
        self.assertFalse(profile.is_deleted)

    def test_cannot_delete_active_student(self):
        _, profile = self._student('a1', reg='R-A1')
        self.client.force_authenticate(self.reception)
        res = self.client.delete(
            reverse('student-profile-detail', args=[profile.pk]),
            {'confirm': True}, format='json',
        )
        self.assertEqual(res.status_code, 409)
        profile.refresh_from_db()
        self.assertFalse(profile.is_deleted)

    def test_cannot_delete_enrolled_student(self):
        _, profile = self._cancelled('a2', 'R-A2', enrol=True)
        self.client.force_authenticate(self.reception)
        res = self.client.delete(
            reverse('student-profile-detail', args=[profile.pk]),
            {'confirm': True}, format='json',
        )
        self.assertEqual(res.status_code, 409)
        profile.refresh_from_db()
        self.assertFalse(profile.is_deleted)

    def test_teacher_cannot_delete_student(self):
        _, profile = self._cancelled('a3', 'R-A3')
        self.client.force_authenticate(self.teacher)
        res = self.client.delete(
            reverse('student-profile-detail', args=[profile.pk]),
            {'confirm': True}, format='json',
        )
        self.assertEqual(res.status_code, 403)
        profile.refresh_from_db()
        self.assertFalse(profile.is_deleted)

    def test_reception_cannot_delete_other_branch_student(self):
        _, profile = self._cancelled('a4', 'R-A4', branch=self.other_branch)
        self.client.force_authenticate(self.reception)  # branch A reception
        res = self.client.delete(
            reverse('student-profile-detail', args=[profile.pk]),
            {'confirm': True}, format='json',
        )
        self.assertIn(res.status_code, (403, 404))
        profile.refresh_from_db()
        self.assertFalse(profile.is_deleted)

    def test_unauthenticated_delete_rejected(self):
        _, profile = self._cancelled('a5', 'R-A5')
        res = self.client.delete(
            reverse('student-profile-detail', args=[profile.pk]),
            {'confirm': True}, format='json',
        )
        self.assertEqual(res.status_code, 401)

    def test_service_level_enforcement(self):
        _, profile = self._cancelled('a6', 'R-A6')
        with self.assertRaises(Exception):
            ProfileService.delete_cancelled_student(actor=self.teacher, profile=profile, confirm=True)
        profile.refresh_from_db()
        self.assertFalse(profile.is_deleted)
