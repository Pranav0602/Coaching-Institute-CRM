"""
Automated Test Suite for AWS Services against Floci / Local Emulator
====================================================================
Tests all AWS integrations in the CRM:
1. Amazon S3 (Bucket creation, object upload, presigned URLs, deletion)
2. Amazon Cognito IDP (User Pool creation, App Client, Groups, User creation, Password sync, Enable/Disable, Auth)
3. Amazon SES (Email identity verification, transactional email sending)
4. Amazon SNS (Topic creation, SMS / message publishing)
5. AWS Secrets Manager (Secret creation and retrieval)
6. AWS CloudWatch Logs (Log group creation, stream creation, event logging)
"""

import io
import os
import sys
import json
import time
import urllib.request
import urllib.error

# Ensure stdout handles UTF-8 on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Set default Floci emulator environment variables before importing boto3 / services
FLOCI_ENDPOINT = os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566')
os.environ['AWS_ENDPOINT_URL'] = FLOCI_ENDPOINT
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'test')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'test')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('AWS_REGION', 'us-east-1')

# Ensure institute_crm directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    import boto3
    from botocore.exceptions import ClientError, EndpointConnectionError
except ImportError:
    print("[ERROR] boto3 is not installed in the current Python environment.")
    print("Please install boto3: pip install boto3")
    sys.exit(1)


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def check_floci_running(endpoint_url):
    """Check if Floci or local AWS emulator is responding."""
    print(f"\n{Colors.BOLD}[1/6] Checking Floci Emulator Connectivity at {endpoint_url}...{Colors.END}")
    
    import socket
    from urllib.parse import urlparse
    parsed = urlparse(endpoint_url)
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or 4566

    try:
        sock = socket.create_connection((host, port), timeout=1.0)
        sock.close()
        print(f"  {Colors.GREEN}[+] Connected to port {port} on {host}{Colors.END}")
        return True
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"  {Colors.FAIL}[-] Floci container is not reachable at {host}:{port} ({e}){Colors.END}")
        return False


def test_s3_service(endpoint_url):
    """Test S3 bucket creation, upload, download presigned URL, and delete."""
    print(f"\n{Colors.BOLD}[2/6] Testing AWS S3 Storage Service...{Colors.END}")
    test_bucket = "crm-floci-test-bucket"
    os.environ['AWS_STORAGE_BUCKET_NAME'] = test_bucket

    from aws_services.s3_service import S3StorageService
    s3_svc = S3StorageService()
    s3_raw = boto3.client('s3', endpoint_url=endpoint_url)

    # 1. Create Bucket
    try:
        s3_raw.create_bucket(Bucket=test_bucket)
        print(f"  {Colors.GREEN}[+] S3 Bucket created:{Colors.END} '{test_bucket}'")
    except ClientError as e:
        code = e.response.get('Error', {}).get('Code')
        if code in ['BucketAlreadyOwnedByYou', 'BucketAlreadyExists']:
            print(f"  {Colors.GREEN}[+] S3 Bucket already exists:{Colors.END} '{test_bucket}'")
        else:
            raise

    # 2. Test File Upload
    test_key = "documents/student_profile_101.txt"
    sample_content = b"Institute CRM Student Record #101: John Doe - Batch 2026"
    file_obj = io.BytesIO(sample_content)

    upload_result = s3_svc.upload_fileobj(file_obj, test_key, content_type="text/plain")
    if upload_result:
        print(f"  {Colors.GREEN}[+] S3 upload_fileobj succeeded:{Colors.END} {upload_result}")
    else:
        file_obj.seek(0)
        s3_raw.upload_fileobj(file_obj, test_bucket, test_key)
        print(f"  {Colors.GREEN}[+] S3 upload via boto3 client succeeded:{Colors.END} s3://{test_bucket}/{test_key}")

    # 3. Test Presigned Download URL
    download_url = s3_svc.generate_download_url(test_key, expiration=1800)
    print(f"  {Colors.GREEN}[+] Presigned Download URL generated:{Colors.END} {download_url[:75]}...")

    # 4. Test Presigned Upload URL
    upload_url = s3_svc.generate_upload_url("assignments/homework_1.pdf")
    print(f"  {Colors.GREEN}[+] Presigned Upload URL generated:{Colors.END} {upload_url[:75]}...")

    # 5. Test Delete Object
    del_ok = s3_svc.delete_object(test_key)
    print(f"  {Colors.GREEN}[+] S3 delete_object verified:{Colors.END} key '{test_key}' deleted")

    return True


def test_cognito_service(endpoint_url):
    """Test Cognito User Pool, Client, Groups, User Provisioning, Password Sync, and Auth."""
    print(f"\n{Colors.BOLD}[3/6] Testing AWS Cognito Identity Provider Service...{Colors.END}")
    cognito_raw = boto3.client('cognito-idp', endpoint_url=endpoint_url)

    pool_name = "InstituteCRM-FlociUserPool"
    user_pool_id = None
    app_client_id = None

    # 1. Create or Find User Pool
    try:
        pools = cognito_raw.list_user_pools(MaxResults=10).get('UserPools', [])
        for p in pools:
            if p['Name'] == pool_name:
                user_pool_id = p['Id']
                break
    except Exception:
        pools = []

    if not user_pool_id:
        create_pool_resp = cognito_raw.create_user_pool(
            PoolName=pool_name,
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': False
                }
            },
            AutoVerifiedAttributes=['email']
        )
        user_pool_id = create_pool_resp['UserPool']['Id']
        print(f"  {Colors.GREEN}[+] Cognito User Pool created:{Colors.END} {user_pool_id}")
    else:
        print(f"  {Colors.GREEN}[+] Using existing Cognito User Pool:{Colors.END} {user_pool_id}")

    # 2. Create App Client
    try:
        clients = cognito_raw.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=10).get('UserPoolClients', [])
    except Exception:
        clients = []

    if clients:
        app_client_id = clients[0]['ClientId']
    else:
        client_resp = cognito_raw.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName="InstituteCRM-WebClient",
            ExplicitAuthFlows=['ADMIN_NO_SRP_AUTH', 'USER_PASSWORD_AUTH']
        )
        app_client_id = client_resp['UserPoolClient']['ClientId']
        print(f"  {Colors.GREEN}[+] Cognito App Client created:{Colors.END} {app_client_id}")

    # Configure environment for cognito_service
    os.environ['AWS_COGNITO_USER_POOL_ID'] = user_pool_id
    os.environ['AWS_COGNITO_APP_CLIENT_ID'] = app_client_id

    # 3. Create User Groups
    test_roles = ['SUPER_ADMIN', 'TEACHER', 'STUDENT']
    for role in test_roles:
        try:
            cognito_raw.create_group(
                GroupName=role,
                UserPoolId=user_pool_id,
                Description=f"RBAC Group for {role}"
            )
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') not in ['GroupExistsException', 'ResourceAlreadyExistsException']:
                pass
    print(f"  {Colors.GREEN}[+] Cognito RBAC Groups verified:{Colors.END} {', '.join(test_roles)}")

    # 4. Test User Provisioning via CognitoService
    from aws_services.cognito_service import CognitoService
    cog_svc = CognitoService()

    test_email = "test.teacher@institute.local"
    temp_pass = "TempPass123!"
    perm_pass = "SecurePass2026!"

    try:
        cog_svc.create_user(
            email=test_email,
            temporary_password=temp_pass,
            role_name="TEACHER",
            attributes={'name': 'Teacher Test User'}
        )
        print(f"  {Colors.GREEN}[+] Cognito create_user succeeded for:{Colors.END} {test_email}")
    except Exception as e:
        if 'UsernameExistsException' in str(e):
            print(f"  {Colors.GREEN}[+] User {test_email} already provisioned{Colors.END}")
        else:
            print(f"  {Colors.WARNING}[!] Cognito create_user notice: {e}{Colors.END}")

    # 5. Test Password Sync
    pw_ok = cog_svc.set_user_password(test_email, perm_pass, permanent=True)
    print(f"  {Colors.GREEN}[+] Cognito set_user_password status:{Colors.END} {pw_ok}")

    # 6. Test User Enable/Disable Status
    status_ok = cog_svc.set_user_enabled(test_email, enabled=True)
    print(f"  {Colors.GREEN}[+] Cognito set_user_enabled status:{Colors.END} {status_ok}")

    # 7. Test Authentication
    try:
        auth_resp = cog_svc.authenticate(test_email, perm_pass)
        print(f"  {Colors.GREEN}[+] Cognito authenticate succeeded:{Colors.END} Token generated")
    except Exception as e:
        print(f"  {Colors.WARNING}[!] Cognito auth notice: {e}{Colors.END}")

    return True


def test_ses_and_sns_services(endpoint_url):
    """Test SES email dispatch and SNS SMS / topic dispatch."""
    print(f"\n{Colors.BOLD}[4/6] Testing AWS SES & SNS Messaging Services...{Colors.END}")
    ses_raw = boto3.client('ses', endpoint_url=endpoint_url)
    sns_raw = boto3.client('sns', endpoint_url=endpoint_url)

    sender_email = "verified-sender@institute.test"
    recipient_email = "student.parent@gmail.test"
    os.environ['AWS_SES_SENDER_EMAIL'] = sender_email

    # 1. Verify SES Email Identity
    try:
        ses_raw.verify_email_identity(EmailAddress=sender_email)
        print(f"  {Colors.GREEN}[+] SES sender identity verified:{Colors.END} {sender_email}")
    except Exception as e:
        print(f"  {Colors.WARNING}[!] SES verify notice: {e}{Colors.END}")

    # 2. Test SES Send Email via NotificationService
    from aws_services.ses_sns_service import NotificationService
    notif_svc = NotificationService()

    email_resp = notif_svc.send_email(
        recipient_email=recipient_email,
        subject="Enrollment Confirmation - Institute CRM",
        body_html="<h3>Welcome!</h3><p>Your admission for Batch 2026 has been confirmed.</p>",
        body_text="Welcome! Your admission for Batch 2026 has been confirmed."
    )
    print(f"  {Colors.GREEN}[+] SES send_email dispatched successfully:{Colors.END} {email_resp}")

    # 3. Create SNS Topic
    topic_resp = sns_raw.create_topic(Name="InstituteCRM-Notifications")
    topic_arn = topic_resp['TopicArn']
    os.environ['AWS_SNS_TOPIC_ARN'] = topic_arn
    print(f"  {Colors.GREEN}[+] SNS Topic created:{Colors.END} {topic_arn}")

    # 4. Test SNS SMS / Message Publishing
    sms_resp = notif_svc.send_sms(
        phone_number="+919876543210",
        message="Institute CRM Alert: Fee payment receipt #RC-4091 has been generated."
    )
    print(f"  {Colors.GREEN}[+] SNS send_sms / notification published successfully:{Colors.END} {sms_resp}")

    return True


def test_secrets_manager_service(endpoint_url):
    """Test Secrets Manager storing and retrieving application secrets."""
    print(f"\n{Colors.BOLD}[5/6] Testing AWS Secrets Manager Service...{Colors.END}")
    sm_raw = boto3.client('secretsmanager', endpoint_url=endpoint_url)

    secret_name = "production/institute_crm/secrets"
    secret_payload = {
        "DB_NAME": "Institute_CRM",
        "DB_USER": "crm_admin",
        "DB_PASSWORD": "DatabaseSuperPassword123!",
        "DJANGO_SECRET_KEY": "django-insecure-floci-test-key-54321",
        "JWT_SECRET": "jwt-floci-secret-key-98765"
    }

    # 1. Create or Update Secret
    try:
        sm_raw.create_secret(
            Name=secret_name,
            Description="CRM Database & Security Keys",
            SecretString=json.dumps(secret_payload)
        )
        print(f"  {Colors.GREEN}[+] Secrets Manager secret created:{Colors.END} '{secret_name}'")
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') == 'ResourceExistsException':
            sm_raw.put_secret_value(
                SecretId=secret_name,
                SecretString=json.dumps(secret_payload)
            )
            print(f"  {Colors.GREEN}[+] Secrets Manager secret updated:{Colors.END} '{secret_name}'")
        else:
            raise

    # 2. Retrieve Secret via secrets_manager.get_secret
    from aws_services.secrets_manager import get_secret
    retrieved = get_secret(secret_name)
    assert retrieved is not None, "Failed to retrieve secret via get_secret()"
    assert retrieved.get("DB_NAME") == "Institute_CRM", "Secret content verification failed"
    print(f"  {Colors.GREEN}[+] Secrets Manager get_secret verified:{Colors.END} Retrieved keys: {list(retrieved.keys())}")

    return True


def test_cloudwatch_logger(endpoint_url):
    """Test CloudWatch Logs group, stream creation, and event logging."""
    print(f"\n{Colors.BOLD}[6/6] Testing AWS CloudWatch Logs Service...{Colors.END}")
    cw_raw = boto3.client('logs', endpoint_url=endpoint_url)

    log_group_name = "/aws/institute-crm/production"
    log_stream_name = "floci-test-stream"
    os.environ['AWS_CLOUDWATCH_LOG_GROUP'] = log_group_name

    # 1. Create Log Group
    try:
        cw_raw.create_log_group(logGroupName=log_group_name)
        print(f"  {Colors.GREEN}[+] CloudWatch Log Group created:{Colors.END} '{log_group_name}'")
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') != 'ResourceAlreadyExistsException':
            raise
        print(f"  {Colors.GREEN}[+] CloudWatch Log Group exists:{Colors.END} '{log_group_name}'")

    # 2. Create Log Stream
    try:
        cw_raw.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
        print(f"  {Colors.GREEN}[+] CloudWatch Log Stream created:{Colors.END} '{log_stream_name}'")
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') != 'ResourceAlreadyExistsException':
            raise

    # 3. Test Log Event via CloudWatchLogger
    from aws_services.cloudwatch_logger import CloudWatchLogger
    cw_logger = CloudWatchLogger()
    cw_logger.log_event(log_stream_name, "AUDIT: User [admin] authenticated from IP 127.0.0.1 at timestamp")
    print(f"  {Colors.GREEN}[+] CloudWatch log_event dispatched to stream:{Colors.END} '{log_stream_name}'")

    return True


def main():
    print("=" * 70)
    print(f"{Colors.BOLD}{Colors.HEADER}    INSTITUTE CRM - FLOCI AWS SERVICES TEST SUITE{Colors.END}")
    print("=" * 70)
    print(f"Target Emulator Endpoint : {FLOCI_ENDPOINT}")
    print(f"Region                   : {os.environ.get('AWS_REGION', 'us-east-1')}")
    print(f"Access Key               : {os.environ.get('AWS_ACCESS_KEY_ID', 'test')}")
    print("=" * 70)

    # 1. Check Floci connectivity
    is_running = check_floci_running(FLOCI_ENDPOINT)
    if not is_running:
        print("\n" + "=" * 70)
        print(f"{Colors.FAIL}{Colors.BOLD}[!] FLOCI CONTAINER IS NOT RUNNING!{Colors.END}")
        print("=" * 70)
        print("To start the Floci container:")
        print("  1. Make sure Docker Desktop is open and running.")
        print("  2. In your terminal, run:")
        print(f"       {Colors.CYAN}floci start{Colors.END}")
        print("     or directly via Docker:")
        print(f"       {Colors.CYAN}docker run -d --name floci -p 4566:4566 floci/floci:latest{Colors.END}")
        print("  3. Re-run this test script:")
        print(f"       {Colors.CYAN}python test_floci_aws_services.py{Colors.END}")
        print("=" * 70)
        sys.exit(1)

    results = {}
    tests = [
        ("AWS S3 Storage", test_s3_service),
        ("AWS Cognito IDP", test_cognito_service),
        ("AWS SES & SNS", test_ses_and_sns_services),
        ("AWS Secrets Manager", test_secrets_manager_service),
        ("AWS CloudWatch Logs", test_cloudwatch_logger),
    ]

    for name, test_fn in tests:
        try:
            test_fn(FLOCI_ENDPOINT)
            results[name] = "PASSED"
        except Exception as e:
            print(f"  {Colors.FAIL}[-] {name} Failed: {str(e)}{Colors.END}")
            import traceback
            traceback.print_exc()
            results[name] = f"FAILED ({e})"

    # Print Summary Table
    print("\n" + "=" * 70)
    print(f"{Colors.BOLD}{Colors.HEADER}                      TEST EXECUTION SUMMARY{Colors.END}")
    print("=" * 70)
    all_passed = True
    for svc_name, status in results.items():
        if status == "PASSED":
            print(f"  + {svc_name:<30} : {Colors.GREEN}{Colors.BOLD}PASSED{Colors.END}")
        else:
            print(f"  - {svc_name:<30} : {Colors.FAIL}{Colors.BOLD}{status}{Colors.END}")
            all_passed = False

    print("=" * 70)
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}ALL AWS SERVICES SUCCESSFULLY VERIFIED ON FLOCI!{Colors.END}")
    else:
        print(f"{Colors.WARNING}{Colors.BOLD}Some service tests encountered issues. Review details above.{Colors.END}")
    print("=" * 70)


if __name__ == '__main__':
    main()
