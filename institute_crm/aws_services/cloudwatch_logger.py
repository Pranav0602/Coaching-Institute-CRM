"""
AWS CloudWatch Logging Handler Integration
Stream central system logs, audit trails, and runtime metrics to AWS CloudWatch Logs.
"""
import os
import logging

logger = logging.getLogger('institute_crm.aws')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
LOG_GROUP_NAME = os.environ.get('AWS_CLOUDWATCH_LOG_GROUP', '/aws/institute-crm/production')

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    BOTO3_AVAILABLE = False

class CloudWatchLogger:
    def __init__(self):
        if BOTO3_AVAILABLE:
            try:
                endpoint = os.environ.get('AWS_ENDPOINT_URL')
                self.client = boto3.client('logs', region_name=AWS_REGION, endpoint_url=endpoint)
                self.enabled = True
            except Exception as e:
                logger.warning(f"AWS CloudWatch fallback enabled: {str(e)}")
                self.client = None
                self.enabled = False
        else:
            self.client = None
            self.enabled = False

    def log_event(self, log_stream, message):
        if not self.enabled:
            logger.info(f"[CLOUDWATCH LOGSTREAM:{log_stream}] {message}")
            return

        group_name = os.environ.get('AWS_CLOUDWATCH_LOG_GROUP', LOG_GROUP_NAME)
        try:
            self.client.put_log_events(
                logGroupName=group_name,
                logStreamName=log_stream,
                logEvents=[
                    {
                        'timestamp': int(logging.time.time() * 1000),
                        'message': message
                    }
                ]
            )
        except Exception as e:
            logger.error(f"CloudWatch put_log_events failed: {str(e)}")

cloudwatch_logger = CloudWatchLogger()
