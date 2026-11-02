# backend/Services/HelpdeskService/resources/storageService.py
import io
import logging
import pathlib
import uuid
from typing import Optional, Tuple
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from configs.base_config import BaseConfig

logger = logging.getLogger(__name__)


class StorageService:
    """Unified storage service supporting Neon S3-compatible Object Storage
    with local disk fallback and transparent caching.
    """

    def __init__(self):
        self._s3_client = None
        self._bucket = BaseConfig.NEON_STORAGE_BUCKET or "storage"
        self._use_neon = (
            BaseConfig.USE_NEON_STORAGE
            and bool(BaseConfig.AWS_ENDPOINT_URL_S3)
            and bool(BaseConfig.AWS_ACCESS_KEY_ID)
            and bool(BaseConfig.AWS_SECRET_ACCESS_KEY)
        )

        if self._use_neon:
            try:
                self._s3_client = boto3.client(
                    "s3",
                    endpoint_url=BaseConfig.AWS_ENDPOINT_URL_S3,
                    aws_access_key_id=BaseConfig.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=BaseConfig.AWS_SECRET_ACCESS_KEY,
                    region_name=BaseConfig.AWS_REGION or "ap-southeast-1",
                    config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
                )
                logger.info(
                    "Neon Object Storage initialized (Bucket: %s, Endpoint: %s)",
                    self._bucket,
                    BaseConfig.AWS_ENDPOINT_URL_S3,
                )
            except Exception as exc:
                logger.error("Failed to initialize Neon Object Storage client: %s. Using local fallback.", exc)
                self._s3_client = None
                self._use_neon = False
        else:
            logger.info("Using local filesystem storage (Path: %s)", BaseConfig.STORAGE_PATH)

    @property
    def is_neon_enabled(self) -> bool:
        return self._use_neon and self._s3_client is not None

    def generate_storage_key(self, doc_id: uuid.UUID, version_number: int, safe_suffix: Optional[str] = None) -> str:
        """Returns standard S3 object key: documents/{doc_id}/v{version_number}_{suffix}.pdf"""
        suffix = safe_suffix or uuid.uuid4().hex[:12]
        return f"documents/{doc_id}/v{version_number}_{suffix}.pdf"

    def put_document_bytes(
        self,
        key: str,
        content: bytes,
        content_type: str = "application/pdf",
        local_path: Optional[pathlib.Path] = None,
    ) -> str:
        """Stores document content to Neon S3 (and caches to local path if provided).
        Returns the resolved storage identifier (S3 key or local path string).
        """
        # Always write to local cache if local_path specified
        if local_path:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(content)

        if self.is_neon_enabled:
            try:
                self._s3_client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=content,
                    ContentType=content_type,
                )
                logger.info("Saved %d bytes to Neon Object Storage at '%s/%s'", len(content), self._bucket, key)
                return f"neon://{self._bucket}/{key}"
            except Exception as exc:
                logger.error("Neon Object Storage put_object failed (%s). Retaining local file.", exc)
                if local_path:
                    return str(local_path)
                raise

        return str(local_path) if local_path else key

    def get_document_bytes(self, storage_path: str) -> bytes:
        """Retrieves document bytes from Neon S3 or local filesystem."""
        if storage_path.startswith("neon://"):
            parts = storage_path.replace("neon://", "").split("/", 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""
            if self.is_neon_enabled:
                resp = self._s3_client.get_object(Bucket=bucket, Key=key)
                return resp["Body"].read()

        # Check local filesystem
        local_p = pathlib.Path(storage_path)
        if local_p.exists():
            return local_p.read_bytes()

        # If it's a key without protocol and Neon is enabled
        if self.is_neon_enabled:
            try:
                resp = self._s3_client.get_object(Bucket=self._bucket, Key=storage_path)
                return resp["Body"].read()
            except ClientError as ce:
                logger.warning("Object not found in Neon S3: %s", ce)

        raise FileNotFoundError(f"Storage path '{storage_path}' cannot be resolved locally or on Neon.")

    def generate_presigned_download_url(
        self,
        storage_path: str,
        expires_in: int = 3600,
        download_filename: Optional[str] = None,
    ) -> Optional[str]:
        """Generates a secure S3 presigned GET URL with custom Content-Disposition header.
        Returns None if Neon S3 is disabled or storage_path is strictly local.
        """
        if not self.is_neon_enabled:
            return None

        key = storage_path
        bucket = self._bucket
        if storage_path.startswith("neon://"):
            parts = storage_path.replace("neon://", "").split("/", 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""

        params = {"Bucket": bucket, "Key": key}
        if download_filename:
            safe_name = download_filename.replace('"', '\\"')
            params["ResponseContentDisposition"] = f'attachment; filename="{safe_name}"'
            params["ResponseContentType"] = "application/pdf"

        try:
            url = self._s3_client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )
            return url
        except Exception as exc:
            logger.error("Failed to generate presigned URL for '%s': %s", key, exc)
            return None


storage_service = StorageService()
