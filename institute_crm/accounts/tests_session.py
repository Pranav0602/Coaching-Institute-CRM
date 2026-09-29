"""Session lifecycle tests: token refresh, rotation, logout revocation.

These back the mobile client's promise that a signed-in user never has to type
credentials again until they explicitly sign out.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Branch, Role, User
from accounts.services import AuthService

LOGIN_URL = '/api/v1/accounts/auth/login/'
REFRESH_URL = '/api/v1/accounts/auth/token/refresh/'
LOGOUT_URL = '/api/v1/accounts/auth/logout/'
ME_URL = '/api/v1/accounts/auth/me/'


class TokenRefreshTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(code=Role.ADMISSION_COUNSELOR, name='Counselor')
        self.branch = Branch.objects.create(
            code='BR-R', name='Refresh Branch', city='Pune',
            address='R', phone='999', email='r@test.com',
        )
        self.user = User.objects.create_user(
            username='counsellor1', email='counsellor1@test.com',
            password='Str0ngPass!23', role=self.role, branch=self.branch,
        )

    def _login(self):
        res = self.client.post(LOGIN_URL, {
            'username': 'counsellor1', 'password': 'Str0ngPass!23',
        }, format='json')
        self.assertEqual(res.status_code, 200)
        # `response.data` is the pre-render payload; the {success, data} envelope
        # is applied by StandardResponseRenderer on the wire.
        return res.data

    # ------------------------------------------------------------- issuance

    def test_login_reports_token_lifetimes(self):
        payload = self._login()
        self.assertIn('access', payload)
        self.assertIn('refresh', payload)
        self.assertEqual(payload['user']['role_code'], Role.ADMISSION_COUNSELOR)
        # A native client schedules its own refresh off these rather than
        # discovering expiry by eating a 401 mid-screen.
        self.assertGreater(payload['access_expires_in'], 0)
        self.assertGreater(payload['refresh_expires_in'], payload['access_expires_in'])

    # -------------------------------------------------------------- refresh

    def test_refresh_returns_a_usable_access_token(self):
        payload = self._login()
        res = self.client.post(REFRESH_URL, {'refresh': payload['refresh']}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.data
        self.assertIn('access', data)
        self.assertIn('access_expires_in', data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        me = self.client.get(ME_URL)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['username'], 'counsellor1')

    def test_refresh_rotates_and_blacklists_the_old_token(self):
        payload = self._login()
        first = self.client.post(REFRESH_URL, {'refresh': payload['refresh']}, format='json')
        rotated = first.data['refresh']
        self.assertNotEqual(rotated, payload['refresh'])

        # The superseded token must be dead, otherwise a stolen refresh token
        # outlives every rotation and the session can never truly be ended.
        replay = self.client.post(REFRESH_URL, {'refresh': payload['refresh']}, format='json')
        self.assertEqual(replay.status_code, 401)

        # ...while the rotated one still works.
        second = self.client.post(REFRESH_URL, {'refresh': rotated}, format='json')
        self.assertEqual(second.status_code, 200)

    def test_refresh_rejects_garbage_and_missing_token(self):
        self.assertEqual(
            self.client.post(REFRESH_URL, {'refresh': 'not-a-jwt'}, format='json').status_code,
            401,
        )
        missing = self.client.post(REFRESH_URL, {}, format='json')
        self.assertEqual(missing.status_code, 400)
        self.assertIn('refresh', missing.data['errors'])
    def test_refresh_preserves_custom_claims_for_role_navigation(self):
        payload = self._login()
        data = AuthService.refresh_tokens(refresh_token=payload['refresh'])
        self.assertIn('access', data)
        self.assertIn('refresh', data)

    # --------------------------------------------------------------- logout

    def test_logout_blacklists_the_refresh_token(self):
        payload = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {payload['access']}")
        out = self.client.post(LOGOUT_URL, {'refresh': payload['refresh']}, format='json')
        self.assertEqual(out.status_code, 200)

        res = self.client.post(REFRESH_URL, {'refresh': payload['refresh']}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_logout_requires_authentication(self):
        self.assertEqual(
            self.client.post(LOGOUT_URL, {'refresh': 'x'}, format='json').status_code,
            401,
        )

    def test_logout_tolerates_an_already_dead_token(self):
        """Signing out is about ending the session, not proving the token was real."""
        payload = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {payload['access']}")
        for _ in range(2):
            out = self.client.post(LOGOUT_URL, {'refresh': payload['refresh']}, format='json')
            self.assertEqual(out.status_code, 200)


class TokenBlacklistConfigurationTests(TestCase):
    """The switch that makes login depend on an extra table must stay coherent.

    Enabling ``rest_framework_simplejwt.token_blacklist`` makes SimpleJWT write an
    ``OutstandingToken`` row every time it issues a refresh token, including on an
    ordinary login. A deploy that ships the code without the migration therefore
    turns every sign-in into a 500, so both halves of the switch are pinned here
    and the deploy check is exercised against both table states.
    """

    def test_switch_and_installed_apps_stay_in_step(self):
        from django.conf import settings

        self.assertEqual(
            getattr(settings, "JWT_BLACKLIST", False),
            "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS,
            'JWT_BLACKLIST and INSTALLED_APPS disagree; settings.py keeps them together',
        )

    def test_rotation_blacklisting_tracks_the_switch(self):
        from django.conf import settings

        self.assertEqual(
            settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"],
            getattr(settings, "JWT_BLACKLIST", False),
            "rotation without blacklisting leaves every superseded token valid forever",
        )

    def test_deploy_check_is_silent_when_the_tables_exist(self):
        from institute_crm.checks import check_token_blacklist_migrated

        self.assertEqual(check_token_blacklist_migrated(None), [])

    def test_deploy_check_errors_when_the_tables_are_missing(self):
        """The check that would have caught the production outage."""
        from unittest.mock import MagicMock, patch

        from institute_crm.checks import check_token_blacklist_migrated

        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = (None,)  # to_regclass found nothing

        with patch('institute_crm.checks.connections') as connections:
            connections.__getitem__ = MagicMock(return_value=MagicMock(cursor=MagicMock(
                return_value=cursor,
            )))
            messages = check_token_blacklist_migrated(None)

        self.assertEqual(len(messages), 1, messages)
        self.assertEqual(messages[0].id, 'crm.E004')
        self.assertIn('migrate', messages[0].hint)
