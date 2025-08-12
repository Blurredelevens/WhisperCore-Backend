import logging
import os
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling S3 file uploads and operations."""

    def __init__(self):
        self.s3_client = None
        self.bucket_name = None
        self._initialize_s3_client()

    def _initialize_s3_client(self):
        """Initialize S3 client with credentials from environment."""
        try:
            # Get S3 configuration from environment
            aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_region = os.getenv("AWS_REGION", "us-east-1")
            self.bucket_name = os.getenv("S3_BUCKET_NAME")

            if not all([aws_access_key_id, aws_secret_access_key, self.bucket_name]):
                logger.warning("S3 credentials not fully configured. S3 uploads will be disabled.")
                return

            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region,
            )
            logger.info("S3 client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None

    def upload_file(self, file, folder: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to S3.

        Args:
            file: File object to upload
            folder: S3 folder path (e.g., 'users', 'memories')
            filename: Optional custom filename, if not provided will use secure_filename

        Returns:
            S3 URL of uploaded file or None if upload failed
        """
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return None

        try:
            # Generate filename if not provided
            if not filename:
                filename = secure_filename(file.filename)
                if not filename:
                    filename = f"file_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"

            # Create S3 key (path)
            s3_key = f"{folder}/{filename}"

            # Upload file to S3
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    "ContentType": file.content_type or "application/octet-stream",
                    "ACL": "public-read",  # Make file publicly accessible
                },
            )

            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            logger.info(f"File uploaded successfully to S3: {s3_url}")
            return s3_url

        except NoCredentialsError:
            logger.error("AWS credentials not found")
            return None
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            return None

    def delete_file(self, s3_url: str) -> bool:
        """
        Delete a file from S3.

        Args:
            s3_url: S3 URL of the file to delete

        Returns:
            True if deletion successful, False otherwise
        """
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return False

        try:
            # Extract key from S3 URL
            # URL format: https://bucket-name.s3.amazonaws.com/folder/filename
            key = s3_url.replace(f"https://{self.bucket_name}.s3.amazonaws.com/", "")

            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"File deleted successfully from S3: {s3_url}")
            return True

        except ClientError as e:
            logger.error(f"S3 deletion failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 deletion: {e}")
            return False

    def upload_user_image(self, file, user_id: int) -> Optional[str]:
        """
        Upload user profile image to S3.

        Args:
            file: Image file object
            user_id: User ID for organizing files

        Returns:
            S3 URL of uploaded image or None if upload failed
        """
        filename = f"user_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
        return self.upload_file(file, "users", filename)

    def upload_memory_image(self, file, memory_id: int, user_id: int) -> Optional[str]:
        """
        Upload memory image to S3.

        Args:
            file: Image file object
            memory_id: Memory ID for organizing files
            user_id: User ID for organizing files

        Returns:
            S3 URL of uploaded image or None if upload failed
        """
        filename = f"memory_{memory_id}_user_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
        return self.upload_file(file, "memories", filename)

    def is_enabled(self) -> bool:
        """Check if S3 service is properly configured and enabled."""
        return self.s3_client is not None and self.bucket_name is not None


# Global S3 service instance
s3_service = S3Service()
