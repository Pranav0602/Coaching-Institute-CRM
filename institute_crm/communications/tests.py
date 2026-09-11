from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Branch, Role, User
from academics.models import Batch, Course, CourseEnrolment, Subject, Timetable
from communications.models import Notification
from communications.services import CommunicationService
from institute_crm.exceptions import PermissionDeniedError
from users_profiles.models import ParentProfile, StudentParent, StudentProfile


class BatchNotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_super = Role.objects.create(code=Role.SUPER_ADMIN, name='Super Admin')
        self.role_branch = Role.objects.create(code=Role.BRANCH_ADMIN, name='Branch Admin')
        self.role_teacher = Role.objects.create(code=Role.TEACHER, name='Teacher')
        self.role_student = Role.objects.create(code=Role.STUDENT, name='Student')
        self.role_parent = Role.objects.create(code=Role.PARENT, name='Parent')

        self.branch_a = Branch.objects.create(
            code='BA', name='Branch A', city='Pune', address='A', phone='111', email='a@test.com')
        self.branch_b = Branch.objects.create(
            code='BB', name='Branch B', city='Mumbai', address='B', phone='222', email='b@test.com')

        self.super_admin = User.objects.create_user(
            username='super', password='pass12345', role=self.role_super, branch=self.branch_a)
        self.branch_admin_a = User.objects.create_user(
            username='badmin_a', password='pass12345', role=self.role_branch, branch=self.branch_a)
        self.branch_admin_b = User.objects.create_user(
            username='badmin_b', password='pass12345', role=self.role_branch, branch=self.branch_b)
        self.teacher = User.objects.create_user(
            username='teacher1', password='pass12345', role=self.role_teacher, branch=self.branch_a)
        self.other_teacher = User.objects.create_user(
            username='teacher2', password='pass12345', role=self.role_teacher, branch=self.branch_a)

        self.course = Course.objects.create(code='CRS1', title='Course 1', total_fee=10000)
        self.batch_a = Batch.objects.create(
            code='BATCH-A1', name='Batch A1', course=self.course, branch=self.branch_a,
            start_date='2026-01-01', end_date='2026-12-31')
        self.batch_b = Batch.objects.create(
            code='BATCH-B1', name='Batch B1', course=self.course, branch=self.branch_b,
            start_date='2026-01-01', end_date='2026-12-31')

        subject = Subject.objects.create(course=self.course, code='SUB1', title='Subject 1')
        Timetable.objects.create(
            batch=self.batch_a, subject=subject, teacher=self.teacher,
            day_of_week='MONDAY', start_time='09:00', end_time='10:00')

        self.student = User.objects.create_user(
            username='stud1', email='stud1@test.com', password='pass12345',
            role=self.role_student, branch=self.branch_a)
        StudentProfile.objects.create(user=self.student, enrollment_number='ENR001', batch=self.batch_a)
        CourseEnrolment.objects.create(
            student=self.student, course=self.course, batch=self.batch_a, status='ACTIVE')

        self.parent_user = User.objects.create_user(
            username='parent1', email='parent1@test.com', password='pass12345',
            role=self.role_parent, branch=self.branch_a)
        parent_profile = ParentProfile.objects.create(user=self.parent_user)
        StudentParent.objects.create(
            student=self.student.student_profile, parent=parent_profile, is_primary=True)

    def test_super_admin_can_send_to_any_batch(self):
        result = CommunicationService.send_batch_notification(
            actor=self.super_admin, batch_id=self.batch_b.id,
            title='Hello', message='World', channel='IN_APP', target_audience='STUDENTS')
        # batch B has no students, so count is 0 but no permission error
        self.assertEqual(result['batch_id'], str(self.batch_b.id))

        result = CommunicationService.send_batch_notification(
            actor=self.super_admin, batch_id=self.batch_a.id,
            title='Hi', message='Batch A', channel='IN_APP', target_audience='STUDENTS')
        self.assertEqual(result['recipient_count'], 1)
        self.assertTrue(Notification.objects.filter(recipient=self.student, batch=self.batch_a).exists())

    def test_branch_admin_own_branch_success_other_blocked(self):
        result = CommunicationService.send_batch_notification(
            actor=self.branch_admin_a, batch_id=self.batch_a.id,
            title='Local', message='Msg', channel='IN_APP', target_audience='STUDENTS')
        self.assertEqual(result['recipient_count'], 1)
        with self.assertRaises(PermissionDeniedError):
            CommunicationService.send_batch_notification(
                actor=self.branch_admin_a, batch_id=self.batch_b.id,
                title='X', message='Y', channel='IN_APP', target_audience='STUDENTS')

    def test_teacher_taught_success_other_blocked(self):
        result = CommunicationService.send_batch_notification(
            actor=self.teacher, batch_id=self.batch_a.id,
            title='Class', message='Tomorrow off', channel='IN_APP', target_audience='STUDENTS')
        self.assertEqual(result['recipient_count'], 1)
        with self.assertRaises(PermissionDeniedError):
            CommunicationService.send_batch_notification(
                actor=self.other_teacher, batch_id=self.batch_a.id,
                title='X', message='Y', channel='IN_APP', target_audience='STUDENTS')

    def test_target_audience_parents_and_all(self):
        res_parents = CommunicationService.send_batch_notification(
            actor=self.super_admin, batch_id=self.batch_a.id,
            title='PTM', message='Meeting', channel='IN_APP', target_audience='PARENTS')
        self.assertEqual(res_parents['recipient_count'], 1)
        self.assertTrue(Notification.objects.filter(recipient=self.parent_user).exists())

        res_all = CommunicationService.send_batch_notification(
            actor=self.super_admin, batch_id=self.batch_a.id,
            title='Both', message='Hi all', channel='IN_APP', target_audience='ALL')
        self.assertEqual(res_all['recipient_count'], 2)

    def test_unread_count_and_mark_all_read(self):
        CommunicationService.send_batch_notification(
            actor=self.super_admin, batch_id=self.batch_a.id,
            title='N1', message='M1', channel='IN_APP', target_audience='STUDENTS')
        self.assertEqual(CommunicationService.get_unread_count(self.student), 1)
        updated = CommunicationService.mark_all_read(self.student)
        self.assertEqual(updated, 1)
        self.assertEqual(CommunicationService.get_unread_count(self.student), 0)

    def test_send_batch_api_and_unread_count_api(self):
        self.client.force_authenticate(user=self.branch_admin_a)
        resp = self.client.post('/api/v1/communications/notifications/send-batch/', {
            'batch_id': str(self.batch_a.id),
            'title': 'API hello',
            'message': 'API world',
            'channel': 'IN_APP',
            'target_audience': 'STUDENTS',
        }, format='json')
        self.assertEqual(resp.status_code, 201)

        self.client.force_authenticate(user=self.student)
        unread = self.client.get('/api/v1/communications/notifications/unread-count/')
        self.assertEqual(unread.status_code, 200)

        mark = self.client.post('/api/v1/communications/notifications/mark-all-read/')
        self.assertEqual(mark.status_code, 200)

        self.client.force_authenticate(user=self.branch_admin_a)
        sent = self.client.get('/api/v1/communications/notifications/sent/')
        self.assertEqual(sent.status_code, 200)
