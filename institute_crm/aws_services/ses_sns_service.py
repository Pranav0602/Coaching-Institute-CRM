"""
AWS SES & AWS SNS Notification Service
Dispatches transactional emails (credentials, fee receipts, announcements) via SES and SMS notifications via SNS.
"""
import os
import logging

logger = logging.getLogger('institute_crm.aws')

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
SES_SENDER_EMAIL = os.environ.get('AWS_SES_SENDER_EMAIL', 'no-reply@coachingcrm.com')
SNS_TOPIC_ARN = os.environ.get('AWS_SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:123456789012:InstituteNotifications')

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = Exception
    BOTO3_AVAILABLE = False

class NotificationService:
    @property
    def ses_client(self):
        if not BOTO3_AVAILABLE:
            return None
        endpoint = os.environ.get('AWS_ENDPOINT_URL')
        region = os.environ.get('AWS_REGION', AWS_REGION)
        try:
            return boto3.client('ses', region_name=region, endpoint_url=endpoint)
        except Exception as e:
            logger.warning(f"AWS SES client initialization failed: {str(e)}")
            return None

    @property
    def sns_client(self):
        if not BOTO3_AVAILABLE:
            return None
        endpoint = os.environ.get('AWS_ENDPOINT_URL')
        region = os.environ.get('AWS_REGION', AWS_REGION)
        try:
            return boto3.client('sns', region_name=region, endpoint_url=endpoint)
        except Exception as e:
            logger.warning(f"AWS SNS client initialization failed: {str(e)}")
            return None

    @property
    def enabled(self):
        return bool(BOTO3_AVAILABLE)

    def send_email(self, recipient_email, subject, body_html, body_text=None):
        sender = os.environ.get('AWS_SES_SENDER_EMAIL', SES_SENDER_EMAIL)
        has_endpoint = bool(os.environ.get('AWS_ENDPOINT_URL'))
        if not self.enabled or (sender == 'no-reply@coachingcrm.com' and not has_endpoint):
            logger.info(f"[MOCK SES EMAIL] Sent to {recipient_email} | Subject: '{subject}'")
            return {"MessageId": f"mock-ses-{recipient_email}"}

        try:
            response = self.ses_client.send_email(
                Source=sender,
                Destination={'ToAddresses': [recipient_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': body_html, 'Charset': 'UTF-8'},
                        'Text': {'Data': body_text or body_html, 'Charset': 'UTF-8'}
                    }
                }
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to send SES email to {recipient_email}: {str(e)}")
            return {"Error": str(e)}

    def send_sms(self, phone_number, message):
        topic_arn = os.environ.get('AWS_SNS_TOPIC_ARN', SNS_TOPIC_ARN)
        has_endpoint = bool(os.environ.get('AWS_ENDPOINT_URL'))
        if not self.enabled or (topic_arn.endswith('123456789012:InstituteNotifications') and not has_endpoint):
            logger.info(f"[MOCK SNS SMS] Sent to {phone_number} | Message: '{message}'")
            return {"MessageId": f"mock-sns-{phone_number}"}

        try:
            response = self.sns_client.publish(
                PhoneNumber=phone_number,
                Message=message
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to send SNS SMS to {phone_number}: {str(e)}")
            return {"Error": str(e)}

notification_service = NotificationService()
