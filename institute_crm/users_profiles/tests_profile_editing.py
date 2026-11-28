"""Full student profile editing: all supported fields, system fields protected, permissions."""
from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from academics.models import Batch, Course
from accounts.models import Branch, Role, User
from users_profiles.models import StudentProfile


def branch(code):
    return Branch.objects.create(code=code, name=f'Branch {code}', city='X', address='A', phone='1', email=f'{code}@x.com')


class StudentProfileEditingTests(APITestCase):
    def setUp(self):
        self.reception_role = Role.objects.get_or_create(code=Role.RECEPTIONIST, defaults={'name': 'Receptionist'})[0]
        self.admin_role = Role.objects.get_or_create(code=Role.BRANCH_ADMIN, defaults={'name': 'Branch Admin'})[0]
        self.student_role = Role.objects.get_or_create(code=Role.STUDENT, defaults={'name': 'Student'})[0]
        self.teacher_role = Role.objects.get_or_create(code=Role.TEACHER, defaults={'name': 'Teacher'})[0]
        self.branch = branch('A')
        self.other = branch('B')
        self.course = Course.objects.create(code='C', title='Course', total_fee=100)
        self.reception = User.objects.create_user(username='rec', password='pw', role=self.reception_role, branch=self.branch)
        self.teacher = User.objects.create_user(username='t', password='pw', role=self.teacher_role, branch=self.branch)
        self.student_user = User.objects.create_user(username='s', password='pw', role=self.student_role, branch=self.branch, first_name='A', last_name='B')
        self.profile = StudentProfile.objects.create(user=self.student_user, reg_no='R1')

    def test_authorized_staff_can_edit_all_supported_fields(self):
        self.client.force_authenticate(self.reception)
        payload = {
            'dob': '2000-01-01', 'gender': 'FEMALE', 'blood_group': 'O+', 'address': 'New Addr',
            'emergency_contact': '999', 'secondary_phone': '888', 'course': str(self.course.pk),
            'academic_branch': 'MECH', 'source_course_label': 'Src', 'source_softwares': 'AutoCAD',
            'documents_url': ['http://x/y.pdf'], 'guardian_name': 'G', 'guardian_phone': '777',
            'guardian_relationship': 'Father', 'agreed_fee': '5000', 'discount_amount': '100',
            'concession_amount': '50', 'scholarship_amount': '200', 'fee_notes': 'note',
        }
        res = self.client.patch(reverse('student-profile-detail', args=[self.profile.pk]), payload, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.gender, 'FEMALE')
        self.assertEqual(self.profile.blood_group, 'O+')
        self.assertEqual(self.profile.address, 'New Addr')
        self.assertEqual(self.profile.course_id, self.course.pk)
        self.assertEqual(self.profile.guardian_name, 'G')
        self.assertEqual(self.profile.documents_url, ['http://x/y.pdf'])
        self.assertEqual(self.profile.agreed_fee, Decimal('5000'))
        self.assertEqual(self.profile.discount_amount, Decimal('100'))
        self.assertEqual(self.profile.fee_notes, 'note')
        self.assertEqual(self.profile.academic_branch, 'MECH')
        self.assertEqual(self.profile.source_softwares, 'AutoCAD')

    def test_system_managed_fields_protected(self):
        self.client.force_authenticate(self.reception)
        before = self.profile.version
        res = self.client.patch(reverse('student-profile-detail', args=[self.profile.pk]), {
            'reg_no': 'HACKED', 'id': 'HACKED', 'user': str(self.teacher.pk),
            'created_at': '1999-01-01', 'is_deleted': True, 'admission_status': 'CANCELLED',
            'deleted_by': str(self.reception.pk), 'cancellation_reason': 'x', 'deletion_reason': 'y',
            'address': 'ok',
        }, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.reg_no, 'R1')
        self.assertEqual(self.profile.user_id, self.student_user.pk)
        self.assertFalse(self.profile.is_deleted)
        self.assertEqual(self.profile.admission_status, 'PENDING')
        self.assertIsNone(self.profile.cancellation_reason)
        self.assertIsNone(self.profile.deletion_reason)
        self.assertEqual(self.profile.address, 'ok')

    def test_unauthorized_users_cannot_edit(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.patch(reverse('student-profile-detail', args=[self.profile.pk]), {'address': 'x'}, format='json')
        self.assertEqual(res.status_code, 403)
        # student themselves cannot edit profile via this endpoint
        self.client.force_authenticate(self.student_user)
        res2 = self.client.patch(reverse('student-profile-detail', args=[self.profile.pk]), {'address': 'y'}, format='json')
        self.assertEqual(res2.status_code, 403)
        self.profile.refresh_from_db()
        self.assertNotEqual(self.profile.address, 'x')

    def test_validation_rejects_bad_values(self):
        self.client.force_authenticate(self.reception)
        res = self.client.patch(reverse('student-profile-detail', args=[self.profile.pk]), {'gender': 'NOPE'}, format='json')
        self.assertIn(res.status_code, (400, 422))
        res = self.client.patch(reverse('student-profile-detail', args=[self.profile.pk]), {'agreed_fee': '-5'}, format='json')
        self.assertIn(res.status_code, (400, 422))
