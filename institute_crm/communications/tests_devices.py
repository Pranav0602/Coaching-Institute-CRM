"""Mobile device push-token registration and student ID-card QR resolution."""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Branch, Role, User
from academics.models import Batch, Course
from communications.models import DeviceToken
from communications.services import CommunicationService
from institute_crm.exceptions import NotFoundError
from users_profiles.models import StudentProfile

REGISTER_URL = '/api/v1/communications/devices/register/'
DEVICES_URL = '/api/v1/communications/devices/'


class DeviceTokenTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(code=Role.STUDENT, name='Student')
        self.role_reception = Role.objects.create(code=Role.RECEPTIONIST, name='Receptionist')
        self.branch = Branch.objects.create(
            code='BR-D', name='Device Branch', city='Pune',
            address='D', phone='888', email='d@test.com',
        )
        self.student = User.objects.create_user(
            username='stud_d1', password='pass12345', role=self.role, branch=self.branch,
        )
        self.other_student = User.objects.create_user(
            username='stud_d2', password='pass12345', role=self.role, branch=self.branch,
        )
        self.reception = User.objects.create_user(
            username='recep1', password='pass12345', role=self.role_reception, branch=self.branch,
        )

    # ------------------------------------------------------------- register

    def test_register_creates_then_idempotently_updates(self):
        """Expo re-sends the same token on every launch, so repeat posts must be 200."""
        self.client.force_authenticate(user=self.student)
        first = self.client.post(REGISTER_URL, {
            'expo_push_token': 'ExponentPushToken[abc123]', 'platform': 'android',
        }, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.data['is_active'])

        second = self.client.post(REGISTER_URL, {
            'expo_push_token': 'ExponentPushToken[abc123]', 'platform': 'android',
            'app_version': '1.2.0',
        }, format='json')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(DeviceToken.objects.count(), 1)
        self.assertEqual(second.data['app_version'], '1.2.0')

    def test_token_reassigned_when_handset_changes_user(self):
        """A shared kiosk install must stop delivering the previous user's alerts."""
        CommunicationService.register_device(
            actor=self.student, expo_push_token='ExponentPushToken[shared]',
        )
        self.client.force_authenticate(user=self.other_student)
        res = self.client.post(REGISTER_URL, {
            'expo_push_token': 'ExponentPushToken[shared]', 'platform': 'ios',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            DeviceToken.objects.get(expo_push_token='ExponentPushToken[shared]').user,
            self.other_student,
        )

    def test_rejects_blank_and_unknown_platform(self):
        self.client.force_authenticate(user=self.student)
        blank = self.client.post(REGISTER_URL, {'expo_push_token': ''}, format='json')
        self.assertEqual(blank.status_code, 400)
        bad = self.client.post(REGISTER_URL, {
            'expo_push_token': 'x', 'platform': 'blackberry',
        }, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_requires_authentication(self):
        self.assertEqual(
            self.client.post(REGISTER_URL, {'expo_push_token': 'x'}, format='json').status_code,
            401,
        )

    # ------------------------------------------------------------- listing

    def test_list_is_scoped_to_the_caller(self):
        CommunicationService.register_device(actor=self.student, expo_push_token='mine-1')
        CommunicationService.register_device(actor=self.other_student, expo_push_token='theirs-1')

        self.client.force_authenticate(user=self.student)
        res = self.client.get(DEVICES_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['expo_push_token'], 'mine-1')

    # ----------------------------------------------------------- unregister

    def test_unregister_deactivates_and_hides_the_token(self):
        device, _ = CommunicationService.register_device(
            actor=self.student, expo_push_token='bye-1',
        )
        self.client.force_authenticate(user=self.student)
        res = self.client.post(f'{DEVICES_URL}{device.pk}/unregister/')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data['is_active'])

        device.refresh_from_db()
        self.assertFalse(device.is_active)
        # A deactivated token must not show up as a live registration.
        self.assertEqual(len(self.client.get(DEVICES_URL).data), 1)

    def test_cannot_unregister_another_users_device(self):
        """A UUID is not an authorisation check - the lookup is scoped to the owner."""
        device, _ = CommunicationService.register_device(
            actor=self.other_student, expo_push_token='not-yours',
        )
        self.client.force_authenticate(user=self.student)
        res = self.client.post(f'{DEVICES_URL}{device.pk}/unregister/')
        self.assertEqual(res.status_code, 404)
        device.refresh_from_db()
        self.assertTrue(device.is_active)

    def test_unregister_all_retires_every_handsset(self):
        CommunicationService.register_device(actor=self.student, expo_push_token='a')
        CommunicationService.register_device(actor=self.student, expo_push_token='b')
        self.client.force_authenticate(user=self.student)
        res = self.client.post(f'{DEVICES_URL}unregister-all/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['retired'], 2)
        self.assertEqual(
            DeviceToken.objects.filter(user=self.student, is_active=True).count(), 0,
        )

    def test_unregister_missing_device_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            CommunicationService.unregister_device(self.student, 'missing-uuid')


class StudentQrTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_student = Role.objects.create(code=Role.STUDENT, name='Student')
        self.role_reception = Role.objects.create(code=Role.RECEPTIONIST, name='Receptionist')
        self.role_teacher = Role.objects.create(code=Role.TEACHER, name='Teacher')
        self.branch = Branch.objects.create(
            code='BR-Q', name='QR Branch', city='Pune',
            address='Q', phone='777', email='q@test.com',
        )
        self.course = Course.objects.create(code='QR1', title='QR Course', total_fee=1000)
        self.batch = Batch.objects.create(
            code='QB1', name='QR Batch', course=self.course, branch=self.branch,
            start_date='2026-01-01', end_date='2026-12-31',
        )
        self.student_user = User.objects.create_user(
            username='qr_stud', password='pass12345', role=self.role_student, branch=self.branch,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user, enrollment_number='ENR/BR-Q/2026/AB12C', batch=self.batch,
        )
        self.reception = User.objects.create_user(
            username='qr_recep', password='pass12345', role=self.role_reception, branch=self.branch,
        )
        self.teacher = User.objects.create_user(
            username='qr_teacher', password='pass12345', role=self.role_teacher, branch=self.branch,
        )

    def test_qr_payload_is_a_stable_deep_link(self):
        self.assertEqual(self.student.qr_payload, 'graphix://student/ENR/BR-Q/2026/AB12C')

    def test_id_card_action_returns_everything_the_card_needs(self):
        self.client.force_authenticate(user=self.reception)
        res = self.client.get(f'/api/v1/profiles/students/{self.student.pk}/id-card/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['enrollment_number'], 'ENR/BR-Q/2026/AB12C')
        self.assertEqual(res.data['qr_payload'], self.student.qr_payload)
        self.assertEqual(res.data['batch_name'], 'QR Batch')
        self.assertEqual(res.data['course_title'], 'QR Course')
        self.assertEqual(res.data['branch_code'], 'BR-Q')

    def test_resolve_qr_matches_a_scanned_card(self):
        self.client.force_authenticate(user=self.reception)
        res = self.client.post('/api/v1/profiles/students/resolve-qr/', {
            'qr_payload': self.student.qr_payload,
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['matched'])
        self.assertEqual(res.data['student']['enrollment_number'], 'ENR/BR-Q/2026/AB12C')

    def test_resolve_qr_rejects_foreign_payloads(self):
        self.client.force_authenticate(user=self.reception)
        res = self.client.post('/api/v1/profiles/students/resolve-qr/', {
            'qr_payload': 'https://evil.example.com/student/1',
        }, format='json')
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.data['matched'])

    def test_resolve_qr_requires_a_payload(self):
        self.client.force_authenticate(user=self.reception)
        res = self.client.post('/api/v1/profiles/students/resolve-qr/', {}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_students_cannot_use_qr_as_an_enumeration_oracle(self):
        """An enrollment number is a lookup key; students must not resolve others'."""
        self.client.force_authenticate(user=self.student_user)
        res = self.client.post('/api/v1/profiles/students/resolve-qr/', {
            'qr_payload': self.student.qr_payload,
        }, format='json')
        self.assertEqual(res.status_code, 403)

    def test_resolve_qr_does_not_leak_another_branch_roster(self):
        other_branch = Branch.objects.create(
            code='BR-Q2', name='Other QR Branch', city='Pune',
            address='Q2', phone='776', email='q2@test.com',
        )
        other_batch = Batch.objects.create(
            code='QB2', name='Other Batch', course=self.course, branch=other_branch,
            start_date='2026-01-01', end_date='2026-12-31',
        )
        other_user = User.objects.create_user(
            username='qr_stud2', password='pass12345', role=self.role_student, branch=other_branch,
        )
        other = StudentProfile.objects.create(
            user=other_user, enrollment_number='ENR/BR-Q2/2026/ZZ99Z', batch=other_batch,
        )

        self.client.force_authenticate(user=self.reception)
        res = self.client.post('/api/v1/profiles/students/resolve-qr/', {
            'qr_payload': other.qr_payload,
        }, format='json')
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.data['matched'])
