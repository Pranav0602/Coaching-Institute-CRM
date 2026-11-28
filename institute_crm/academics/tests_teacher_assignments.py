"""Teacher assignment + scoping + dashboard tests."""
from datetime import date, time

from django.urls import reverse
from rest_framework.test import APITestCase

from academics.models import Batch, Course, CourseEnrolment, Subject, TeacherAssignment, Timetable
from academics.services.teacher_assignment_service import TeacherAssignmentService
from accounts.models import AuditLog, Branch, Role, User
from users_profiles.models import StudentProfile


def branch(code):
    return Branch.objects.create(code=code, name=f'Branch {code}', city='X', address='A', phone='1', email=f'{code}@x.com')


class TeacherAssignmentTests(APITestCase):
    def setUp(self):
        self.admin_role = Role.objects.get_or_create(code=Role.BRANCH_ADMIN, defaults={'name': 'Branch Admin'})[0]
        self.super_role = Role.objects.get_or_create(code=Role.SUPER_ADMIN, defaults={'name': 'Super Admin'})[0]
        self.teacher_role = Role.objects.get_or_create(code=Role.TEACHER, defaults={'name': 'Teacher'})[0]
        self.student_role = Role.objects.get_or_create(code=Role.STUDENT, defaults={'name': 'Student'})[0]

        self.branch_a = branch('A')
        self.branch_b = branch('B')

        self.course_a = Course.objects.create(code='CA', title='Course A', total_fee=100)
        self.course_b = Course.objects.create(code='CB', title='Course B', total_fee=100)
        self.course_c = Course.objects.create(code='CC', title='Course C', total_fee=100)

        self.batch_a = Batch.objects.create(course=self.course_a, branch=self.branch_a, code='BA', name='BA', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))
        self.batch_b = Batch.objects.create(course=self.course_b, branch=self.branch_b, code='BB', name='BB', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))
        # Course C has no batch at branch A -> cannot be selected for branch A.
        self.batch_c_b = Batch.objects.create(course=self.course_c, branch=self.branch_b, code='BC', name='BC', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))

        self.admin_a = User.objects.create_user(username='admin_a', password='pw', role=self.admin_role, branch=self.branch_a)
        self.super_admin = User.objects.create_user(username='super', password='pw', role=self.super_role)
        self.teacher = User.objects.create_user(username='teacher', password='pw', role=self.teacher_role, branch=self.branch_a)

    def _assign(self, **kw):
        return TeacherAssignmentService.assign(actor=kw.pop('actor', self.admin_a), **kw)

    def test_branch_admin_assigns_teacher_to_branch_and_courses(self):
        created = self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)])
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].course_id, self.course_a.pk)
        self.assertEqual(created[0].branch_id, self.branch_a.pk)
        self.assertTrue(AuditLog.objects.filter(action='CREATE', model_name='TeacherAssignment').exists())

    def test_multi_course_assignment_in_one_request(self):
        # add a second course to branch A
        Course.objects.create(code='CA2', title='Course A2', total_fee=1)
        batch_a2_course = Course.objects.get(code='CA2')
        Batch.objects.create(course=batch_a2_course, branch=self.branch_a, code='BA2', name='BA2', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))
        created = self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk), str(batch_a2_course.pk)])
        self.assertEqual(len(created), 2)

    def test_course_must_belong_to_branch(self):
        from institute_crm.exceptions import ValidationFailed
        with self.assertRaises(ValidationFailed):
            self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_b.pk)])
        with self.assertRaises(ValidationFailed):
            self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_c.pk)])

    def test_course_required(self):
        from institute_crm.exceptions import ValidationFailed
        with self.assertRaises(ValidationFailed):
            self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[])

    def test_duplicate_assignment_rejected(self):
        from institute_crm.exceptions import ConflictError
        self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)])
        with self.assertRaises(ConflictError):
            self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)])
        self.assertEqual(TeacherAssignment.objects.filter(is_deleted=False).count(), 1)

    def test_duplicate_ids_in_payload_collapsed(self):
        created = self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk), str(self.course_a.pk)])
        self.assertEqual(len(created), 1)

    def test_only_teacher_role_can_be_assigned(self):
        from institute_crm.exceptions import ValidationFailed
        non_teacher = User.objects.create_user(username='x', password='pw', role=self.student_role, branch=self.branch_a)
        with self.assertRaises(ValidationFailed):
            self._assign(teacher=non_teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)])

    def test_branch_admin_cannot_assign_cross_branch(self):
        from institute_crm.exceptions import PermissionDeniedError
        with self.assertRaises(PermissionDeniedError):
            self._assign(teacher=self.teacher, branch=self.branch_b, course_ids=[str(self.course_b.pk)])

    def test_teacher_in_other_branch_rejected(self):
        from institute_crm.exceptions import ValidationFailed
        other = User.objects.create_user(username='tb', password='pw', role=self.teacher_role, branch=self.branch_b)
        with self.assertRaises(ValidationFailed):
            self._assign(teacher=other, branch=self.branch_a, course_ids=[str(self.course_a.pk)])

    def test_teacher_cannot_self_assign(self):
        from institute_crm.exceptions import PermissionDeniedError
        with self.assertRaises(PermissionDeniedError):
            TeacherAssignmentService.assign(actor=self.teacher, teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)])

    def test_super_admin_system_wide(self):
        created = TeacherAssignmentService.assign(
            actor=self.super_admin, teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)]
        )
        self.assertEqual(len(created), 1)

    def test_removal_soft_deletes_and_recreate_allowed(self):
        created = self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)])
        assignment = created[0]
        TeacherAssignmentService.remove_assignment(actor=self.admin_a, assignment=assignment)
        assignment.refresh_from_db()
        self.assertTrue(assignment.is_deleted)
        self.assertEqual(TeacherAssignmentService.assigned_scope(self.teacher)['course_ids'], set())
        self.assertTrue(AuditLog.objects.filter(action='DELETE', model_name='TeacherAssignment').exists())
        # re-create after removal
        again = self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)])
        self.assertEqual(len(again), 1)

    def test_assigned_scope_union_with_existing_batch_links(self):
        # teacher on a batch without any explicit TeacherAssignment
        self.batch_a.teachers.add(self.teacher)
        scope = TeacherAssignmentService.assigned_scope(self.teacher)
        self.assertIn(self.course_a.pk, scope['course_ids'])
        self.assertIn(self.batch_a.pk, scope['batch_ids'])

    def test_teacher_with_no_assignments_ok(self):
        scope = TeacherAssignmentService.assigned_scope(self.teacher)
        self.assertEqual(scope['course_ids'], set())
        self.assertEqual(scope['batch_ids'], set())

    # --------------------------------------------------------------- API

    def test_api_create_and_scoping(self):
        self.client.force_authenticate(self.admin_a)
        res = self.client.post(reverse('teacher-assignment-list'), {
            'teacher': str(self.teacher.pk),
            'branch': str(self.branch_a.pk),
            'course_ids': [str(self.course_a.pk)],
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        # duplicate -> 409
        res2 = self.client.post(reverse('teacher-assignment-list'), {
            'teacher': str(self.teacher.pk),
            'branch': str(self.branch_a.pk),
            'course_ids': [str(self.course_a.pk)],
        }, format='json')
        self.assertEqual(res2.status_code, 409, res2.data)

    def test_api_cross_branch_forbidden(self):
        self.client.force_authenticate(self.admin_a)
        res = self.client.post(reverse('teacher-assignment-list'), {
            'teacher': str(self.teacher.pk),
            'branch': str(self.branch_b.pk),
            'course_ids': [str(self.course_b.pk)],
        }, format='json')
        self.assertEqual(res.status_code, 403, res.data)

    def test_api_course_not_in_branch_rejected(self):
        self.client.force_authenticate(self.admin_a)
        res = self.client.post(reverse('teacher-assignment-list'), {
            'teacher': str(self.teacher.pk),
            'branch': str(self.branch_a.pk),
            'course_ids': [str(self.course_b.pk)],
        }, format='json')
        self.assertEqual(res.status_code, 400, res.data)

    def test_teacher_sees_only_own_assignments(self):
        created = self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)])
        self.client.force_authenticate(self.teacher)
        res = self.client.get(reverse('teacher-assignment-my'))
        self.assertEqual(res.status_code, 200)
        data = res.data['data'] if isinstance(res.data, dict) and 'data' in res.data else res.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], str(created[0].pk))
        # teacher cannot list another teacher's
        res2 = self.client.get(reverse('teacher-assignment-list'), {'teacher_id': '00000000-0000-0000-0000-000000000000'})
        body2 = res2.data['data'] if isinstance(res2.data, dict) and 'data' in res2.data else res2.data
        ids = [a['teacher'] for a in body2]
        self.assertNotIn('00000000-0000-0000-0000-000000000000', ids)

    def test_teacher_cannot_modify_assignments(self):
        created = self._assign(teacher=self.teacher, branch=self.branch_a, course_ids=[str(self.course_a.pk)])
        self.client.force_authenticate(self.teacher)
        res = self.client.delete(reverse('teacher-assignment-detail', args=[created[0].pk]))
        self.assertEqual(res.status_code, 403)

    def test_available_courses_scoped_to_branch(self):
        self.client.force_authenticate(self.admin_a)
        res = self.client.get(reverse('teacher-assignment-available-courses'), {'branch_id': str(self.branch_a.pk)})
        self.assertEqual(res.status_code, 200)
        data = res.data['data'] if isinstance(res.data, dict) and 'data' in res.data else res.data
        codes = {c['code'] for c in data}
        self.assertIn('CA', codes)
        self.assertNotIn('CB', codes)
        # cannot inspect another branch
        res2 = self.client.get(reverse('teacher-assignment-available-courses'), {'branch_id': str(self.branch_b.pk)})
        self.assertEqual(res2.status_code, 403)


class TeacherDashboardTests(APITestCase):
    def setUp(self):
        self.teacher_role = Role.objects.get_or_create(code=Role.TEACHER, defaults={'name': 'Teacher'})[0]
        self.student_role = Role.objects.get_or_create(code=Role.STUDENT, defaults={'name': 'Student'})[0]
        self.admin_role = Role.objects.get_or_create(code=Role.BRANCH_ADMIN, defaults={'name': 'Branch Admin'})[0]
        self.branch = branch('T')
        self.other = branch('O')
        self.course_a = Course.objects.create(code='CA', title='Course A', total_fee=100)
        self.course_b = Course.objects.create(code='CB', title='Course B', total_fee=100)
        self.batch_a = Batch.objects.create(course=self.course_a, branch=self.branch, code='BA', name='BA', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))
        self.batch_b = Batch.objects.create(course=self.course_b, branch=self.branch, code='BB', name='BB', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))
        # batch in another branch on same course - must NOT leak to teacher
        self.batch_other = Batch.objects.create(course=self.course_a, branch=self.other, code='BO', name='BO', start_date=date(2026, 1, 1), end_date=date(2026, 12, 1))

        self.teacher = User.objects.create_user(username='t', password='pw', role=self.teacher_role, branch=self.branch)
        self.admin = User.objects.create_user(username='a', password='pw', role=self.admin_role, branch=self.branch)

        TeacherAssignment.objects.create(teacher=self.teacher, branch=self.branch, course=self.course_a)

        # subject + schedule on assigned course
        self.subject = Subject.objects.create(course=self.course_a, code='S1', title='Subject One')
        Timetable.objects.create(batch=self.batch_a, subject=self.subject, teacher=self.teacher, day_of_week='MONDAY', start_time=time(9, 0), end_time=time(10, 0))

        # student enrolled in assigned course at own branch
        self.student = User.objects.create_user(username='s', password='pw', role=self.student_role, branch=self.branch, first_name='Sam', last_name='Lee')
        StudentProfile.objects.create(user=self.student, reg_no='R1', batch=self.batch_a)
        CourseEnrolment.objects.create(student=self.student, course=self.course_a, batch=self.batch_a, status='ACTIVE')
        # student in OTHER branch on same course - must not leak
        other_student = User.objects.create_user(username='so', password='pw', role=self.student_role, branch=self.other)
        CourseEnrolment.objects.create(student=other_student, course=self.course_a, batch=self.batch_other, status='ACTIVE')

    def test_dashboard_scoped_to_own_assignments(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.get(reverse('teacher-dashboard-list'))
        self.assertEqual(res.status_code, 200, res.data)
        data = res.data['data'] if isinstance(res.data, dict) and 'data' in res.data else res.data
        # only assigned course A
        codes = {c['course_code'] for c in data['assigned_courses']}
        self.assertEqual(codes, {'CA'})
        self.assertNotIn('CB', codes)
        # students only own branch
        student_names = {s['username'] for c in data['assigned_courses'] for s in c['students']}
        self.assertIn('s', student_names)
        self.assertNotIn('so', student_names)
        # branch info
        self.assertEqual(data['assigned_branch'], self.branch.name)
        # schedule own batch only
        batch_names = {s['batch_name'] for s in data['schedule']}
        self.assertNotIn('BO', batch_names)
        # summary
        self.assertEqual(data['summary']['assigned_courses'], 1)

    def test_non_teacher_cannot_view(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(reverse('teacher-dashboard-list'))
        self.assertEqual(res.status_code, 403)

    def test_teacher_with_no_assignments_empty_dashboard(self):
        bare = User.objects.create_user(username='bare', password='pw', role=self.teacher_role, branch=self.branch)
        self.client.force_authenticate(bare)
        res = self.client.get(reverse('teacher-dashboard-list'))
        self.assertEqual(res.status_code, 200, res.data)
        data = res.data['data'] if isinstance(res.data, dict) and 'data' in res.data else res.data
        self.assertEqual(data['assigned_courses'], [])
        self.assertEqual(data['summary']['assigned_courses'], 0)
