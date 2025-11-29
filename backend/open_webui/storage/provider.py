import os
import shutil
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import BinaryIO, Tuple, Dict

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    # Log will be initialized later, use print for early import
    import sys
    print("Warning: minio library not installed. MinIO storage provider will not be available.", file=sys.stderr)
from open_webui.config import (
    S3_ACCESS_KEY_ID,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
    S3_KEY_PREFIX,
    S3_REGION_NAME,
    S3_SECRET_ACCESS_KEY,
    S3_USE_ACCELERATE_ENDPOINT,
    S3_ADDRESSING_STYLE,
    S3_ENABLE_TAGGING,
    GCS_BUCKET_NAME,
    GOOGLE_APPLICATION_CREDENTIALS_JSON,
    AZURE_STORAGE_ENDPOINT,
    AZURE_STORAGE_CONTAINER_NAME,
    AZURE_STORAGE_KEY,
    STORAGE_PROVIDER,
    UPLOAD_DIR,
    MINIO_HOST,
    MINIO_PORT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
    MINIO_BUCKET_RAW_DATA,
    MINIO_BUCKET_RAG,
    MINIO_BUCKET_ASSETS,
    MINIO_BUCKET_EXTERNAL,
)
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound
from open_webui.constants import ERROR_MESSAGES
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from open_webui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class StorageProvider(ABC):
    @abstractmethod
    def get_file(self, file_path: str) -> str:
        pass

    @abstractmethod
    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        pass

    @abstractmethod
    def delete_all_files(self) -> None:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> None:
        pass


class LocalStorageProvider(StorageProvider):
    @staticmethod
    def upload_file(
        file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)
        # 物理文件保存到绝对路径
        absolute_file_path = os.path.join(UPLOAD_DIR, filename)
        with open(absolute_file_path, "wb") as f:
            f.write(contents)
        # 返回相对路径用于数据库存储
        return contents, filename

    @staticmethod
    def get_file(file_path: str) -> str:
        """Handles downloading of the file from local storage."""
        # 如果是绝对路径，检查是否在 UPLOAD_DIR 下（兼容旧数据）
        if os.path.isabs(file_path):
            try:
                upload_dir_str = str(UPLOAD_DIR)
                # 尝试从绝对路径中提取相对路径
                if upload_dir_str in file_path:
                    relative_path = os.path.relpath(file_path, upload_dir_str)
                    return os.path.join(upload_dir_str, relative_path)
                # 如果不在 UPLOAD_DIR 下，直接返回（可能是外部路径）
                return file_path
            except ValueError:
                # 如果无法计算相对路径，直接返回
                return file_path
        # 如果是相对路径，加上 UPLOAD_DIR
        return os.path.join(str(UPLOAD_DIR), file_path)

    @staticmethod
    def delete_file(file_path: str) -> None:
        """Handles deletion of the file from local storage."""
        filename = file_path.split("/")[-1]
        file_path = f"{UPLOAD_DIR}/{filename}"
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            log.warning(f"File {file_path} not found in local storage.")

    @staticmethod
    def delete_all_files() -> None:
        """Handles deletion of all files from local storage."""
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    log.exception(f"Failed to delete {file_path}. Reason: {e}")
        else:
            log.warning(f"Directory {UPLOAD_DIR} not found in local storage.")


class S3StorageProvider(StorageProvider):
    def __init__(self):
        config = Config(
            s3={
                "use_accelerate_endpoint": S3_USE_ACCELERATE_ENDPOINT,
                "addressing_style": S3_ADDRESSING_STYLE,
            },
            # KIT change - see https://github.com/boto/boto3/issues/4400#issuecomment-2600742103∆
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )

        # If access key and secret are provided, use them for authentication
        if S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                "s3",
                region_name=S3_REGION_NAME,
                endpoint_url=S3_ENDPOINT_URL,
                aws_access_key_id=S3_ACCESS_KEY_ID,
                aws_secret_access_key=S3_SECRET_ACCESS_KEY,
                config=config,
            )
        else:
            # If no explicit credentials are provided, fall back to default AWS credentials
            # This supports workload identity (IAM roles for EC2, EKS, etc.)
            self.s3_client = boto3.client(
                "s3",
                region_name=S3_REGION_NAME,
                endpoint_url=S3_ENDPOINT_URL,
                config=config,
            )

        self.bucket_name = S3_BUCKET_NAME
        self.key_prefix = S3_KEY_PREFIX if S3_KEY_PREFIX else ""

    @staticmethod
    def sanitize_tag_value(s: str) -> str:
        """Only include S3 allowed characters."""
        return re.sub(r"[^a-zA-Z0-9 äöüÄÖÜß\+\-=\._:/@]", "", s)

    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        """Handles uploading of the file to S3 storage."""
        _, file_path = LocalStorageProvider.upload_file(file, filename, tags)
        s3_key = os.path.join(self.key_prefix, filename)
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            if S3_ENABLE_TAGGING and tags:
                sanitized_tags = {
                    self.sanitize_tag_value(k): self.sanitize_tag_value(v)
                    for k, v in tags.items()
                }
                tagging = {
                    "TagSet": [
                        {"Key": k, "Value": v} for k, v in sanitized_tags.items()
                    ]
                }
                self.s3_client.put_object_tagging(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Tagging=tagging,
                )
            return (
                open(file_path, "rb").read(),
                f"s3://{self.bucket_name}/{s3_key}",
            )
        except ClientError as e:
            raise RuntimeError(f"Error uploading file to S3: {e}")

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from S3 storage."""
        try:
            s3_key = self._extract_s3_key(file_path)
            local_file_path = self._get_local_file_path(s3_key)
            self.s3_client.download_file(self.bucket_name, s3_key, local_file_path)
            return local_file_path
        except ClientError as e:
            raise RuntimeError(f"Error downloading file from S3: {e}")

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from S3 storage."""
        try:
            s3_key = self._extract_s3_key(file_path)
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        except ClientError as e:
            raise RuntimeError(f"Error deleting file from S3: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from S3 storage."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            if "Contents" in response:
                for content in response["Contents"]:
                    # Skip objects that were not uploaded from open-webui in the first place
                    if not content["Key"].startswith(self.key_prefix):
                        continue

                    self.s3_client.delete_object(
                        Bucket=self.bucket_name, Key=content["Key"]
                    )
        except ClientError as e:
            raise RuntimeError(f"Error deleting all files from S3: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()

    # The s3 key is the name assigned to an object. It excludes the bucket name, but includes the internal path and the file name.
    def _extract_s3_key(self, full_file_path: str) -> str:
        return "/".join(full_file_path.split("//")[1].split("/")[1:])

    def _get_local_file_path(self, s3_key: str) -> str:
        return f"{UPLOAD_DIR}/{s3_key.split('/')[-1]}"


class GCSStorageProvider(StorageProvider):
    def __init__(self):
        self.bucket_name = GCS_BUCKET_NAME

        if GOOGLE_APPLICATION_CREDENTIALS_JSON:
            self.gcs_client = storage.Client.from_service_account_info(
                info=json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
            )
        else:
            # if no credentials json is provided, credentials will be picked up from the environment
            # if running on local environment, credentials would be user credentials
            # if running on a Compute Engine instance, credentials would be from Google Metadata server
            self.gcs_client = storage.Client()
        self.bucket = self.gcs_client.bucket(GCS_BUCKET_NAME)

    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        """Handles uploading of the file to GCS storage."""
        contents, file_path = LocalStorageProvider.upload_file(file, filename, tags)
        try:
            blob = self.bucket.blob(filename)
            blob.upload_from_filename(file_path)
            return contents, "gs://" + self.bucket_name + "/" + filename
        except GoogleCloudError as e:
            raise RuntimeError(f"Error uploading file to GCS: {e}")

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from GCS storage."""
        try:
            filename = file_path.removeprefix("gs://").split("/")[1]
            local_file_path = f"{UPLOAD_DIR}/{filename}"
            blob = self.bucket.get_blob(filename)
            blob.download_to_filename(local_file_path)

            return local_file_path
        except NotFound as e:
            raise RuntimeError(f"Error downloading file from GCS: {e}")

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from GCS storage."""
        try:
            filename = file_path.removeprefix("gs://").split("/")[1]
            blob = self.bucket.get_blob(filename)
            blob.delete()
        except NotFound as e:
            raise RuntimeError(f"Error deleting file from GCS: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from GCS storage."""
        try:
            blobs = self.bucket.list_blobs()

            for blob in blobs:
                blob.delete()

        except NotFound as e:
            raise RuntimeError(f"Error deleting all files from GCS: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()


class AzureStorageProvider(StorageProvider):
    def __init__(self):
        self.endpoint = AZURE_STORAGE_ENDPOINT
        self.container_name = AZURE_STORAGE_CONTAINER_NAME
        storage_key = AZURE_STORAGE_KEY

        if storage_key:
            # Configure using the Azure Storage Account Endpoint and Key
            self.blob_service_client = BlobServiceClient(
                account_url=self.endpoint, credential=storage_key
            )
        else:
            # Configure using the Azure Storage Account Endpoint and DefaultAzureCredential
            # If the key is not configured, then the DefaultAzureCredential will be used to support Managed Identity authentication
            self.blob_service_client = BlobServiceClient(
                account_url=self.endpoint, credential=DefaultAzureCredential()
            )
        self.container_client = self.blob_service_client.get_container_client(
            self.container_name
        )

    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        """Handles uploading of the file to Azure Blob Storage."""
        contents, file_path = LocalStorageProvider.upload_file(file, filename, tags)
        try:
            blob_client = self.container_client.get_blob_client(filename)
            blob_client.upload_blob(contents, overwrite=True)
            return contents, f"{self.endpoint}/{self.container_name}/{filename}"
        except Exception as e:
            raise RuntimeError(f"Error uploading file to Azure Blob Storage: {e}")

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from Azure Blob Storage."""
        try:
            filename = file_path.split("/")[-1]
            local_file_path = f"{UPLOAD_DIR}/{filename}"
            blob_client = self.container_client.get_blob_client(filename)
            with open(local_file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
            return local_file_path
        except ResourceNotFoundError as e:
            raise RuntimeError(f"Error downloading file from Azure Blob Storage: {e}")

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from Azure Blob Storage."""
        try:
            filename = file_path.split("/")[-1]
            blob_client = self.container_client.get_blob_client(filename)
            blob_client.delete_blob()
        except ResourceNotFoundError as e:
            raise RuntimeError(f"Error deleting file from Azure Blob Storage: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from Azure Blob Storage."""
        try:
            blobs = self.container_client.list_blobs()
            for blob in blobs:
                self.container_client.delete_blob(blob.name)
        except Exception as e:
            raise RuntimeError(f"Error deleting all files from Azure Blob Storage: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()


class MinIOStorageProvider(StorageProvider):
    """MinIO storage provider supporting multiple buckets for different use cases."""
    
    # Bucket mapping for different file types
    BUCKETS = {
        "raw-data": MINIO_BUCKET_RAW_DATA,
        "knowledge": MINIO_BUCKET_RAG,  # Knowledge base files bucket (renamed from "rag")
        "assets": MINIO_BUCKET_ASSETS,
        "external": MINIO_BUCKET_EXTERNAL,
    }
    
    def __init__(self):
        if not MINIO_AVAILABLE:
            raise RuntimeError("minio library is not installed. Please install it with: pip install minio")
        
        # Build MinIO endpoint
        endpoint = f"{MINIO_HOST}:{MINIO_PORT}"
        if "://" not in endpoint:
            endpoint = endpoint.replace("http://", "").replace("https://", "")
        
        # Initialize MinIO client
        self.minio_client = Minio(
            endpoint,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        
        # Ensure all buckets exist
        self._ensure_buckets_exist()
    
    def _ensure_buckets_exist(self):
        """Create buckets if they don't exist."""
        for bucket_name in self.BUCKETS.values():
            try:
                if not self.minio_client.bucket_exists(bucket_name):
                    self.minio_client.make_bucket(bucket_name)
                    log.info(f"Created MinIO bucket: {bucket_name}")
            except S3Error as e:
                log.error(f"Error creating MinIO bucket {bucket_name}: {e}")
                raise RuntimeError(f"Failed to create MinIO bucket {bucket_name}: {e}")
    
    def _get_bucket_for_file(self, filename: str, tags: Dict[str, str] = None) -> str:
        """Determine which bucket to use based on file type or tags.
        
        Bucket selection strategy:
        - rag: Knowledge base files (collection_name in tags)
        - assets: Generated images (image_generation source, not from chat)
        - raw-data: Chat files (chat source or chat_id) or general uploads (default)
        - external: External API sync data
        """
        if tags:
            # Check explicit bucket hint
            bucket_hint = tags.get("bucket", tags.get("bucket_type"))
            if bucket_hint and bucket_hint in self.BUCKETS:
                return self.BUCKETS[bucket_hint]
            
            # Knowledge base files -> knowledge bucket (优先级最高)
            if tags.get("collection_name") or tags.get("OpenWebUI-Collection-Name"):
                return self.BUCKETS["knowledge"]
            
            # Chat files (including images uploaded in chat) -> raw-data bucket
            if (tags.get("source") == "chat" or 
                tags.get("chat_id") or 
                tags.get("OpenWebUI-Chat-Id")):
                return self.BUCKETS["raw-data"]
            
            # Generated images (not from chat) -> assets bucket
            if tags.get("source") == "image_generation":
                return self.BUCKETS["assets"]
            
            # External sync -> external bucket
            if tags.get("source") == "external" or tags.get("external_sync"):
                return self.BUCKETS["external"]
        
        # Default to raw-data for general files
        return self.BUCKETS["raw-data"]
    
    def _extract_minio_path(self, file_path: str) -> Tuple[str, str]:
        """Extract bucket and object key from MinIO path.
        
        Returns:
            Tuple of (bucket_name, object_key)
        """
        # Handle minio://bucket/key format
        if file_path.startswith("minio://"):
            path_parts = file_path[8:].split("/", 1)
            if len(path_parts) == 2:
                return path_parts[0], path_parts[1]
        
        # Handle legacy format or assume raw-data bucket
        # Format: bucket/object_key or just object_key
        if "/" in file_path:
            parts = file_path.split("/", 1)
            if parts[0] in self.BUCKETS.values():
                return parts[0], parts[1]
        
        # Default: assume raw-data bucket
        return self.BUCKETS["raw-data"], file_path
    
    def upload_file(
        self, file: BinaryIO, filename: str, tags: Dict[str, str]
    ) -> Tuple[bytes, str]:
        """Handles uploading of the file to MinIO storage.
        
        Path strategy:
        - raw-data: chat/{user_id}/{filename} (for chat files) or raw/{user_id}/{filename} (for general uploads)
        - knowledge: knowledge/{kb_id}/{file_id}.{ext}
        - assets: assets/{user_id}/{file_id}.{ext} or assets/{user_id}/{filename}
        - external: external/{source_id}/{filename}
        """
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)
        
        # Determine bucket
        bucket_name = self._get_bucket_for_file(filename, tags)
        
        # Generate object key based on bucket and tags
        object_key = self._generate_object_key(filename, bucket_name, tags)
        
        # Upload to MinIO
        try:
            from io import BytesIO
            file_obj = BytesIO(contents)
            self.minio_client.put_object(
                bucket_name,
                object_key,
                file_obj,
                length=len(contents),
                content_type=tags.get("content_type", "application/octet-stream")
            )
            
            # Return MinIO path format: minio://bucket/key
            minio_path = f"minio://{bucket_name}/{object_key}"
            log.info(f"Uploaded file to MinIO: {minio_path}")
            return contents, minio_path
        except S3Error as e:
            raise RuntimeError(f"Error uploading file to MinIO: {e}")
    
    def _generate_object_key(self, filename: str, bucket_name: str, tags: Dict[str, str]) -> str:
        """Generate object key based on bucket and file type.
        
        Path strategies:
        - raw-data: chat/{user_id}/{filename} (for chat files) or raw/{user_id}/{filename} (for general uploads)
        - knowledge: knowledge/{kb_id}/{file_id}.{ext}
        - assets: assets/{user_id}/{file_id}.{ext} or assets/{user_id}/{filename}
        - external: external/{source_id}/{filename}
        """
        import os
        file_ext = os.path.splitext(filename)[1]
        file_id = tags.get("OpenWebUI-File-Id", "")
        user_id = tags.get("OpenWebUI-User-Id", "")
        
        if bucket_name == self.BUCKETS["knowledge"]:
            # Knowledge base files: knowledge/{kb_id}/{file_id}.{ext}
            kb_id = tags.get("collection_name") or tags.get("OpenWebUI-Collection-Name") or "default"
            if file_id:
                return f"knowledge/{kb_id}/{file_id}{file_ext}"
            return f"knowledge/{kb_id}/{filename}"
        
        elif bucket_name == self.BUCKETS["assets"]:
            # Generated images (not from chat): assets/{user_id}/{file_id}.{ext}
            if file_id and user_id:
                return f"assets/{user_id}/{file_id}{file_ext}"
            if user_id:
                return f"assets/{user_id}/{filename}"
            return f"assets/{filename}"
        
        elif bucket_name == self.BUCKETS["external"]:
            # External sync: external/{source_id}/{filename}
            source_id = tags.get("source_id") or tags.get("external_source_id") or "default"
            return f"external/{source_id}/{filename}"
        
        else:  # raw-data
            # Chat files: chat/{user_id}/{filename}
            if tags.get("source") == "chat" or tags.get("chat_id") or tags.get("OpenWebUI-Chat-Id"):
                if user_id:
                    return f"chat/{user_id}/{filename}"
                return f"chat/{filename}"
            # General uploads: raw/{user_id}/{filename}
            if user_id:
                return f"raw/{user_id}/{filename}"
            return f"raw/{filename}"
    
    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from MinIO storage."""
        try:
            bucket_name, object_key = self._extract_minio_path(file_path)
            
            # Download to local temporary file
            local_file_path = os.path.join(str(UPLOAD_DIR), object_key.split("/")[-1])
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            self.minio_client.fget_object(bucket_name, object_key, local_file_path)
            log.info(f"Downloaded file from MinIO: {file_path} -> {local_file_path}")
            return local_file_path
        except S3Error as e:
            raise RuntimeError(f"Error downloading file from MinIO: {e}")
    
    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from MinIO storage."""
        try:
            bucket_name, object_key = self._extract_minio_path(file_path)
            self.minio_client.remove_object(bucket_name, object_key)
            log.info(f"Deleted file from MinIO: {file_path}")
        except S3Error as e:
            raise RuntimeError(f"Error deleting file from MinIO: {e}")
        
        # Always delete from local storage if exists
        try:
            LocalStorageProvider.delete_file(file_path)
        except Exception:
            pass  # Ignore local file deletion errors
    
    def delete_all_files(self) -> None:
        """Handles deletion of all files from MinIO storage."""
        try:
            for bucket_name in self.BUCKETS.values():
                try:
                    objects = self.minio_client.list_objects(bucket_name, recursive=True)
                    for obj in objects:
                        self.minio_client.remove_object(bucket_name, obj.object_name)
                    log.info(f"Deleted all files from MinIO bucket: {bucket_name}")
                except S3Error as e:
                    log.warning(f"Error deleting files from bucket {bucket_name}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error deleting all files from MinIO: {e}")
        
        # Always delete from local storage
        LocalStorageProvider.delete_all_files()


def get_storage_provider(storage_provider: str):
    if storage_provider == "local":
        Storage = LocalStorageProvider()
    elif storage_provider == "s3":
        Storage = S3StorageProvider()
    elif storage_provider == "gcs":
        Storage = GCSStorageProvider()
    elif storage_provider == "azure":
        Storage = AzureStorageProvider()
    elif storage_provider == "minio":
        Storage = MinIOStorageProvider()
    else:
        raise RuntimeError(f"Unsupported storage provider: {storage_provider}")
    return Storage


Storage = get_storage_provider(STORAGE_PROVIDER)
