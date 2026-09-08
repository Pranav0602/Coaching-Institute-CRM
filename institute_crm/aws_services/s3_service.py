"""
AWS S3 Storage Integration Service
Handles file uploads for assignments, student documents, photos, study materials, and presigned URL generation.

Operating modes
---------------
* **Live** - boto3 present, a real bucket configured. Objects are stored privately;
  access is granted only through short-lived presigned URLs.
* **Mock** - boto3 missing, or the bucket left at its placeholder name. Every method
  returns a deterministic fake URL and logs at INFO. This keeps local development and the
  test suite working without AWS credentials, and is why callers must treat a returned
  URL as advisory rather than proof of upload.

Objects are stored with private ACLs by default. Never build a permanent public URL for
learner documents - use :meth:`generate_download_url` behind the same entitlement check
that guards the record itself.
"""
import mimetypes
import os
import logging

logger = logging.getLogger('institute_crm.aws')

S3_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'institute-crm-storage-bucket')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

#: The placeholder value shipped in the repo. While the bucket still equals this, the
#: service stays in mock mode even if boto3 and credentials happen to be available.
PLACEHOLDER_BUCKET = 'institute-crm-storage-bucket'

AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL')

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = Exception
    BOTO3_AVAILABLE = False


class S3StorageService:
    @property
    def s3_client(self):
        if not BOTO3_AVAILABLE:
            return None
        endpoint = os.environ.get('AWS_ENDPOINT_URL')
        region = os.environ.get('AWS_REGION', AWS_REGION)
        try:
            return boto3.client('s3', region_name=region, endpoint_url=endpoint)
        except Exception as e:
            logger.warning(f"AWS S3 client initialization failed: {str(e)}")
            return None

    @property
    def enabled(self):
        return bool(BOTO3_AVAILABLE)

    @property
    def is_live(self) -> bool:
        """True only when a real client and a real (non-placeholder) bucket or custom endpoint are present."""
        bucket = os.environ.get('AWS_STORAGE_BUCKET_NAME', S3_BUCKET_NAME)
        has_endpoint = bool(os.environ.get('AWS_ENDPOINT_URL'))
        return bool(self.enabled and self.s3_client and (bucket != PLACEHOLDER_BUCKET or has_endpoint))

    def object_url(self, key: str) -> str:
        """Canonical (non-presigned) object URL. Useful for storing a reference only."""
        return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key.lstrip('/')}"

    def upload_fileobj(self, fileobj, key: str, content_type: str | None = None) -> str | None:
        """Stream an open file object to S3 and return its object URL.

        Returns ``None`` when the upload could not be performed, so callers can treat S3
        as an optional mirror rather than a hard dependency. Used by
        ``UserService._mirror_to_s3`` for profile photos.

        The object is written private; read access goes through
        :meth:`generate_download_url`.
        """
        if not key:
            logger.warning("upload_fileobj called without a key; skipping")
            return None

        if not self.is_live:
            logger.info(f"[MOCK S3] Would upload {key}")
            return None

        guessed_type = content_type or mimetypes.guess_type(key)[0] or 'application/octet-stream'
        try:
            try:
                fileobj.seek(0)
            except (AttributeError, OSError):
                # Some file-likes are not seekable; upload from the current position.
                pass

            self.s3_client.upload_fileobj(
                fileobj,
                S3_BUCKET_NAME,
                key,
                ExtraArgs={'ContentType': guessed_type, 'ACL': 'private'},
            )
            logger.info(f"Uploaded {key} to s3://{S3_BUCKET_NAME}")
            return self.object_url(key)
        except Exception as e:
            # Callers keep a locally stored copy, so this is recoverable.
            logger.error(f"Failed to upload {key} to S3: {str(e)}")
            return None

    def delete_object(self, key: str) -> bool:
        """Delete an object. Returns True when S3 confirms, False otherwise."""
        if not key or not self.is_live:
            logger.info(f"[MOCK S3] Would delete {key}")
            return False
        try:
            self.s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete {key} from S3: {str(e)}")
            return False

    def generate_upload_url(self, file_path, expiration=3600):
        if not self.is_live:
            logger.info(f"[MOCK S3] Presigned upload URL generated for {file_path}")
            return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/uploads/{file_path}?mock_presigned=true"

        try:
            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': file_path},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned upload URL: {str(e)}")
            return f"https://storage.institute-crm.com/{file_path}"

    def generate_download_url(self, file_path, expiration=3600):
        if not self.is_live:
            return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/uploads/{file_path}?mock_download=true"

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': file_path},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned download URL: {str(e)}")
            return f"https://storage.institute-crm.com/{file_path}"


s3_service = S3StorageService()
