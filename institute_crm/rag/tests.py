from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, Branch, User
from academics.models import Course
from rag.models import KnowledgeDocument


class CounselorSyllabusAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role_admin = Role.objects.create(code=Role.SUPER_ADMIN, name='Super Admin')
        self.role_branch = Role.objects.create(code=Role.BRANCH_ADMIN, name='Branch Admin')
        self.role_counselor = Role.objects.create(code=Role.ADMISSION_COUNSELOR, name='Counselor')
        self.branch = Branch.objects.create(
            code='BR-T1', name='Test Campus', city='Pune',
            address='Test', phone='1234567890', email='t@t.com',
        )
        self.admin = User.objects.create_user(
            username='adm1', password='pass12345', role=self.role_admin, branch=self.branch,
        )
        self.counselor = User.objects.create_user(
            username='coun1', password='pass12345', role=self.role_counselor, branch=self.branch,
        )
        self.course = Course.objects.create(
            code='TST-101', title='Test Full Stack', duration_months=6, total_fee=50000,
            field_of_engineering='IT & Software Development',
        )
        self.published = KnowledgeDocument.objects.create(
            title='Syllabus: Test Full Stack (TST-101)',
            category='STUDY_GUIDE',
            content='Module 1: HTML\nModule 2: JS',
            is_published=True,
            metadata_json={'course_id': str(self.course.id), 'tools': ['React', 'Python']},
        )
        self.draft = KnowledgeDocument.objects.create(
            title='Draft policy',
            category='ADMISSION_POLICY',
            content='secret draft',
            is_published=False,
            metadata_json={},
        )

    def test_admission_counselor_can_list_published_documents(self):
        self.client.force_authenticate(user=self.counselor)
        res = self.client.get('/api/v1/rag/documents/')
        self.assertEqual(res.status_code, 200)
        data = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        # Handle paginated or envelope shapes
        if isinstance(data, dict) and 'results' in data:
            data = data['results']
        titles = [d['title'] for d in data]
        self.assertIn(self.published.title, titles)
        self.assertNotIn(self.draft.title, titles)

    def test_admission_counselor_cannot_create_document(self):
        self.client.force_authenticate(user=self.counselor)
        res = self.client.post('/api/v1/rag/documents/', {
            'title': 'Hack', 'category': 'GENERAL', 'content': 'x',
        }, format='json')
        self.assertEqual(res.status_code, 403)

    def test_admission_counselor_cannot_edit_or_delete_document(self):
        self.client.force_authenticate(user=self.counselor)
        res = self.client.patch(f'/api/v1/rag/documents/{self.published.pk}/', {'title': 'Edited'}, format='json')
        self.assertEqual(res.status_code, 403)
        res = self.client.delete(f'/api/v1/rag/documents/{self.published.pk}/')
        self.assertEqual(res.status_code, 403)

    def test_counselor_can_filter_documents_by_category_and_course(self):
        self.client.force_authenticate(user=self.counselor)
        res = self.client.get('/api/v1/rag/documents/', {'category': 'STUDY_GUIDE'})
        self.assertEqual(res.status_code, 200)
        data = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        if isinstance(data, dict) and 'results' in data:
            data = data['results']
        self.assertTrue(all(d['category'] == 'STUDY_GUIDE' for d in data))

        res = self.client.get('/api/v1/rag/documents/', {'course_id': str(self.course.id)})
        self.assertEqual(res.status_code, 200)
        data = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        if isinstance(data, dict) and 'results' in data:
            data = data['results']
        self.assertTrue(any(d['id'] == str(self.published.pk) for d in data))

        res = self.client.get('/api/v1/rag/documents/', {'search': 'HTML'})
        self.assertEqual(res.status_code, 200)

    def test_admin_retains_full_crud(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/v1/rag/documents/', {
            'title': 'Admin doc', 'category': 'GENERAL', 'content': 'hello world',
            'is_published': True,
        }, format='json')
        self.assertIn(res.status_code, (200, 201))
        doc_id = res.data.get('id', getattr(res.data.get('data', {}), 'get', lambda *a, **k: None)('id')) if isinstance(res.data, dict) else None
        if not doc_id and isinstance(res.data, dict) and 'data' in res.data:
            doc_id = res.data['data'].get('id')
        self.assertIsNotNone(doc_id)
        res = self.client.patch(f'/api/v1/rag/documents/{doc_id}/', {'title': 'Admin doc v2'}, format='json')
        self.assertEqual(res.status_code, 200)
        res = self.client.delete(f'/api/v1/rag/documents/{doc_id}/')
        self.assertIn(res.status_code, (200, 204))

    def test_course_syllabus_action_for_counselor(self):
        self.client.force_authenticate(user=self.counselor)
        res = self.client.get(f'/api/v1/academics/courses/{self.course.pk}/syllabus/')
        self.assertEqual(res.status_code, 200)
        payload = res.data.get('data', res.data) if isinstance(res.data, dict) else res.data
        self.assertIn('content', payload)
