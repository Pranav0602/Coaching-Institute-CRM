"""
AWS Secrets Manager Utility
Retrieves production database credentials, JWT secrets, and API keys securely from AWS Secrets Manager.
"""
import os
import json
import logging

logger = logging.getLogger('institute_crm.aws')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    BOTO3_AVAILABLE = False

def get_secret(secret_name):
    if not BOTO3_AVAILABLE:
        return None

    try:
        endpoint = os.environ.get('AWS_ENDPOINT_URL')
        client = boto3.client('secretsmanager', region_name=AWS_REGION, endpoint_url=endpoint)
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in get_secret_value_response:
            return json.loads(get_secret_value_response['SecretString'])
    except Exception as e:
        logger.warning(f"Unable to retrieve AWS secret '{secret_name}', falling back to env vars: {str(e)}")
        return None
