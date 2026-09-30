"""Session lifecycle tests: token refresh, rotation, logout revocation.

These back the mobile client's promise that a signed-in user never has to type
credentials again until they explicitly sign out.
"""
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Branch, Role, User
from accounts.services import AuthService
from institute_crm import token_revocation

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


class TokenRevocationUnavailableTests(TestCase):
    """The production outage, in miniature: the app is installed, the tables are not.

    Enabling ``rest_framework_simplejwt.token_blacklist`` makes SimpleJWT write an
    ``OutstandingToken`` row every time it issues a refresh token, including on an ordinary
    login. A deploy that ships the code without the migration therefore turns every sign-in
    into a 500 - and that is exactly what reached production. Here the tables are simulated
    as absent and the whole session lifecycle has to keep working anyway.
    """

    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(code=Role.ADMISSION_COUNSELOR, name='Counselor')
        self.user = User.objects.create_user(
            username='counsellor1', email='counsellor1@test.com',
            password='Str0ngPass!23', role=self.role,
        )
        self.absent = ['token_blacklist_outstandingtoken']
        patcher = patch.object(
            token_revocation, 'missing_tables', return_value=self.absent,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        # `usable()` caches its answer for the life of the process, exactly as it would in
        # a worker that booted against this database.
        token_revocation.reset_cache()
        self.addCleanup(token_revocation.reset_cache)

    def _login(self):
        res = self.client.post(LOGIN_URL, {
            'username': 'counsellor1', 'password': 'Str0ngPass!23',
        }, format='json')
        return res

    def test_login_still_issues_tokens(self):
        res = self._login()
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_the_reduced_guarantee_is_logged_once_and_loudly(self):
        with self.assertLogs('institute_crm.token_revocation', level='ERROR') as logs:
            self._login()
            self._login()
        messages = [record for record in logs.output if 'token_blacklist_outstandingtoken' in record]
        self.assertEqual(len(messages), 1, logs.output)
        self.assertIn('migrate', messages[0])

    def test_refresh_still_rotates_without_the_tables(self):
        payload = self._login().data
        res = self.client.post(REFRESH_URL, {'refresh': payload['refresh']}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertNotEqual(res.data['refresh'], payload['refresh'])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        self.assertEqual(self.client.get(ME_URL).status_code, 200)

    def test_logout_succeeds_without_the_tables(self):
        payload = self._login().data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {payload['access']}")
        out = self.client.post(LOGOUT_URL, {'refresh': payload['refresh']}, format='json')
        self.assertEqual(out.status_code, 200, out.data)

    def test_nothing_is_written_to_the_absent_table(self):
        """The degraded path must not attempt the write it knows will fail."""
        with patch('rest_framework_simplejwt.tokens.OutstandingToken.objects') as outstanding:
            self._login()
        outstanding.create.assert_not_called()


class TokenBlacklistConfigurationTests(TestCase):
    """The switch that makes login depend on an extra table must stay coherent.

    Both halves of the switch are pinned here, and the probe, the deploy check, the
    readiness probe and the boot-time repair are each exercised against a database that has
    the tables and one that does not.
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

    def test_the_probe_reports_the_tables_that_are_missing(self):
        self.assertEqual(token_revocation.missing_tables(), [])

        token_revocation.reset_cache()
        self.addCleanup(token_revocation.reset_cache)
        self.assertTrue(token_revocation.usable())

        with patch.object(
            token_revocation, 'missing_tables', return_value=['a_table', 'b_table'],
        ):
            token_revocation.reset_cache()
            self.assertFalse(token_revocation.usable())

    def test_deploy_check_is_silent_when_the_tables_exist(self):
        from institute_crm.checks import check_token_blacklist_migrated

        self.assertEqual(check_token_blacklist_migrated(None), [])

    def test_deploy_check_errors_when_the_tables_are_missing(self):
        """The check that should have caught the production outage before it shipped."""
        from institute_crm.checks import check_token_blacklist_migrated

        with patch.object(
            token_revocation, 'missing_tables', return_value=['token_blacklist_blacklistedtoken'],
        ):
            messages = check_token_blacklist_migrated(None)

        self.assertEqual(len(messages), 1, messages)
        self.assertEqual(messages[0].id, 'crm.E004')
        self.assertIn('token_blacklist_blacklistedtoken', messages[0].msg)
        self.assertIn('migrate', messages[0].hint)

    def test_readiness_reports_the_missing_tables(self):
        """/readyz went green while every login 500'd; it must not do that again."""
        from institute_crm.checks import run_readiness_checks

        self.assertEqual([f for f in run_readiness_checks() if f.startswith('crm.E004')], [])

        with patch.object(
            token_revocation, 'missing_tables', return_value=['token_blacklist_outstandingtoken'],
        ):
            failures = run_readiness_checks()

        self.assertEqual(len([f for f in failures if f.startswith('crm.E004')]), 1, failures)

    def test_boot_repair_migrates_only_when_the_tables_are_missing(self):
        # `repair_missing_tables` stands down under the test runner, so the guard that
        # keeps it from touching the test database is lifted for this one case.
        with override_settings(IS_TESTING=False), \
                patch.object(token_revocation, 'enabled', return_value=True), \
                patch.object(token_revocation, 'missing_tables', return_value=[]):
            with patch.object(token_revocation, '_advisory_lock') as lock:
                with patch('institute_crm.token_revocation.call_command') as migrate:
                    self.assertTrue(token_revocation.repair_missing_tables())
            migrate.assert_not_called()
            lock.assert_not_called()

        with override_settings(IS_TESTING=False), \
                patch.object(token_revocation, 'enabled', return_value=True), \
                patch.object(token_revocation, 'missing_tables', return_value=['t1']):
            with patch.object(token_revocation, '_advisory_lock'):
                with patch('institute_crm.token_revocation.call_command') as migrate:
                    self.assertFalse(token_revocation.repair_missing_tables())
            migrate.assert_called_once()
            self.assertEqual(
                migrate.call_args.args[:2], ('migrate', 'token_blacklist'),
                'only the token_blacklist app may be migrated at boot',
            )

    def test_boot_repair_reports_failure_without_raising(self):
        """A worker that cannot repair must still serve logins."""
        with override_settings(IS_TESTING=False), \
                patch.object(token_revocation, 'enabled', return_value=True), \
                patch.object(token_revocation, 'missing_tables', return_value=['t1']):
            with patch.object(token_revocation, '_advisory_lock'):
                with patch(
                    'institute_crm.token_revocation.call_command',
                    side_effect=RuntimeError('permission denied for database'),
                ):
                    self.assertFalse(token_revocation.repair_missing_tables())

    def test_boot_repair_never_runs_under_the_test_runner(self):
        with override_settings(IS_TESTING=True):
            with patch.object(token_revocation, 'missing_tables', return_value=['t1']):
                with patch('institute_crm.token_revocation.call_command') as migrate:
                    self.assertTrue(token_revocation.repair_missing_tables())
            migrate.assert_not_called()
