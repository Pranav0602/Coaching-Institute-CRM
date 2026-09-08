"""
AWS Cognito Integration Service.

Cognito is a *mirror*, not the authority: Django's ``User`` table authenticates every
request (see ``accounts.services.auth_service``). This module keeps Cognito in step so a
future cut-over to hosted auth does not strand existing accounts.

Operating modes
---------------
* **Live** - boto3 present and a real user pool configured.
* **Mock** - boto3 missing, or the pool id left at its placeholder. Calls log at INFO and
  return a deterministic fake result so development and tests need no AWS credentials.

Every mirroring method returns a boolean rather than raising: a Cognito outage must never
roll back a local change the user already completed.
"""
import os
import logging

logger = logging.getLogger('institute_crm.aws')

COGNITO_USER_POOL_ID = os.environ.get('AWS_COGNITO_USER_POOL_ID', 'us-east-1_mockPoolId')
COGNITO_APP_CLIENT_ID = os.environ.get('AWS_COGNITO_APP_CLIENT_ID', 'mockAppClientId')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = Exception
    BOTO3_AVAILABLE = False

#: Placeholder pool shipped in the repo. While the pool id still equals this, the service
#: stays in mock mode even if boto3 and credentials happen to be present.
PLACEHOLDER_POOL_ID = 'us-east-1_mockPoolId'


class CognitoService:
    @property
    def client(self):
        if not BOTO3_AVAILABLE:
            return None
        endpoint = os.environ.get('AWS_ENDPOINT_URL')
        region = os.environ.get('AWS_REGION', AWS_REGION)
        try:
            return boto3.client('cognito-idp', region_name=region, endpoint_url=endpoint)
        except Exception as e:
            logger.warning(f"AWS Cognito client initialization failed: {str(e)}")
            return None

    @property
    def enabled(self):
        return bool(BOTO3_AVAILABLE)

    @property
    def is_live(self) -> bool:
        """True only when a real client and a real (non-placeholder) user pool exist."""
        pool_id = os.environ.get('AWS_COGNITO_USER_POOL_ID', COGNITO_USER_POOL_ID)
        has_endpoint = bool(os.environ.get('AWS_ENDPOINT_URL'))
        return bool(self.enabled and self.client and (pool_id != PLACEHOLDER_POOL_ID or has_endpoint))

    def set_user_password(self, username: str, password: str, permanent: bool = True) -> bool:
        """Overwrite a Cognito user's password to match the local one.

        Django remains the authority for authentication in this deployment; Cognito is kept
        in step so a future cut-over does not strand every account. Returns True when
        Cognito confirms, False otherwise - never raises, because a mirror failure must not
        roll back a password change the user already completed locally.

        ``AuthService._sync_cognito_password`` probes for this method with ``getattr``, so
        the signature (keyword ``username``/``password``/``permanent``) is a contract.
        """
        if not username or not password:
            return False

        if not self.is_live:
            logger.info(f"[MOCK COGNITO] Would set password for {username}")
            return False

        try:
            self.client.admin_set_user_password(
                UserPoolId=COGNITO_USER_POOL_ID,
                Username=username,
                Password=password,
                Permanent=bool(permanent),
            )
            logger.info(f"Cognito password synchronised for {username}")
            return True
        except Exception as e:
            # Deliberately broad: any AWS-side problem is non-fatal here.
            logger.error(f"Failed to sync Cognito password for {username}: {str(e)}")
            return False

    def set_user_enabled(self, username: str, enabled: bool) -> bool:
        """Enable or disable a Cognito user, mirroring a local activate/soft-delete."""
        if not username:
            return False
        if not self.is_live:
            logger.info(f"[MOCK COGNITO] Would {'enable' if enabled else 'disable'} {username}")
            return False
        try:
            call = self.client.admin_enable_user if enabled else self.client.admin_disable_user
            call(UserPoolId=COGNITO_USER_POOL_ID, Username=username)
            return True
        except Exception as e:
            logger.error(f"Failed to update Cognito status for {username}: {str(e)}")
            return False

    def create_user(self, email, temporary_password, role_name, attributes=None):
        if not self.is_live:
            logger.info(f"[MOCK COGNITO] Provisioned Cognito user: {email} with role {role_name}")
            return {"User": {"Username": email, "UserStatus": "CONFIRMED", "Sub": f"cognito-sub-{email}"}}

        try:
            user_attrs = [
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
            ]
            if attributes:
                for k, v in attributes.items():
                    user_attrs.append({'Name': k, 'Value': str(v)})

            response = self.client.admin_create_user(
                UserPoolId=COGNITO_USER_POOL_ID,
                Username=email,
                UserAttributes=user_attrs,
                TemporaryPassword=temporary_password,
                DesiredDeliveryMediums=['EMAIL']
            )

            try:
                self.client.admin_add_user_to_group(
                    UserPoolId=COGNITO_USER_POOL_ID,
                    Username=email,
                    GroupName=role_name
                )
            except ClientError as ce:
                if getattr(ce, 'response', {}).get('Error', {}).get('Code') == 'ResourceNotFoundException':
                    self.client.create_group(
                        GroupName=role_name,
                        UserPoolId=COGNITO_USER_POOL_ID,
                        Description=f"Group for {role_name}"
                    )
                    self.client.admin_add_user_to_group(
                        UserPoolId=COGNITO_USER_POOL_ID,
                        Username=email,
                        GroupName=role_name
                    )

            return response
        except ClientError as e:
            logger.error(f"Error creating Cognito user {email}: {str(e)}")
            raise Exception(f"Cognito User Provisioning Error: {getattr(e, 'response', {}).get('Error', {}).get('Message', str(e))}")

    def authenticate(self, username, password):
        if not self.is_live:
            logger.info(f"[MOCK COGNITO] Authenticated user {username}")
            return {
                "AccessToken": f"mock-access-token-{username}",
                "RefreshToken": f"mock-refresh-token-{username}",
                "IdToken": f"mock-id-token-{username}",
                "ExpiresIn": 3600
            }

        try:
            response = self.client.admin_initiate_auth(
                UserPoolId=COGNITO_USER_POOL_ID,
                ClientId=COGNITO_APP_CLIENT_ID,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            return response.get('AuthenticationResult', {})
        except ClientError as e:
            logger.error(f"Cognito Authentication Failed for {username}: {str(e)}")
            raise Exception(getattr(e, 'response', {}).get('Error', {}).get('Message', str(e)))

cognito_service = CognitoService()
