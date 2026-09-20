import uuid
import hashlib
import asyncio
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any, Dict, List
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import settings

class ObjectStorageService(ABC):
    @abstractmethod
    async def upload_file_stream(
        self, bucket: str, key: str, file_generator: AsyncGenerator[bytes, None], content_type: str = "audio/wav"
    ) -> Dict[str, Any]:
        """Streams file payload and calculates SHA-256 inline in a single pass."""
        pass

    @abstractmethod
    async def generate_upload_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        """Generates a secure presigned upload URL for direct client-to-S3 uploads."""
        pass

    @abstractmethod
    async def generate_download_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        """Generates a secure presigned download URL for playback."""
        pass

    @abstractmethod
    async def exists(self, bucket: str, key: str) -> bool:
        """Checks if a file exists in the object storage."""
        pass

    @abstractmethod
    async def head(self, bucket: str, key: str) -> Dict[str, Any]:
        """Retrieves head metadata of the object."""
        pass

    @abstractmethod
    async def copy(self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> None:
        """Copies an object from one location to another."""
        pass

    @abstractmethod
    async def move(self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> None:
        """Moves/Renames an object."""
        pass

    @abstractmethod
    async def download_stream(self, bucket: str, key: str) -> AsyncGenerator[bytes, None]:
        """Downloads an object as a stream of bytes."""
        pass

    @abstractmethod
    async def write_chunk(self, bucket: str, key: str, data: bytes) -> None:
        """Writes a single binary chunk of audio directly to object store."""
        pass

    @abstractmethod
    async def merge_session_chunks(self, bucket: str, source_prefix: str, destination_key: str, expected_count: int) -> Dict[str, Any]:
        """Merges temporary chunk parts into a single destination file."""
        pass

    @abstractmethod
    async def download_object(self, bucket: str, key: str) -> bytes:
        """Downloads an entire object and returns it as raw bytes."""
        pass


class MinIOStorageService(ObjectStorageService):
    def __init__(self):
        # Configure client config for MinIO compatibility (uses path style routing)
        self.s3_config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"}
        )
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ROOT_USER,
            aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
            config=self.s3_config
        )
        # External client endpoint for generating presigned URLs reachable from client/localhost
        self.external_client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_EXTERNAL_ENDPOINT,
            aws_access_key_id=settings.MINIO_ROOT_USER,
            aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
            config=self.s3_config
        )

    async def upload_file_stream(
        self, bucket: str, key: str, file_generator: AsyncGenerator[bytes, None], content_type: str = "audio/wav"
    ) -> Dict[str, Any]:
        # Ensure the target bucket exists before starting upload
        await asyncio.to_thread(self._ensure_bucket_exists, bucket)

        # Initialize S3 Multipart Upload
        multipart_upload = await asyncio.to_thread(
            self.client.create_multipart_upload,
            Bucket=bucket,
            Key=key,
            ContentType=content_type
        )
        upload_id = multipart_upload["UploadId"]
        parts: List[Dict[str, Any]] = []

        sha256_hash = hashlib.sha256()
        part_number = 1
        current_chunk_data = bytearray()
        total_size = 0

        # S3 min part size is 5MB
        MIN_PART_SIZE = 5 * 1024 * 1024

        try:
            async for chunk in file_generator:
                current_chunk_data.extend(chunk)
                sha256_hash.update(chunk)
                total_size += len(chunk)

                # If current buffer meets or exceeds the minimum part size, upload it
                if len(current_chunk_data) >= MIN_PART_SIZE:
                    part = await asyncio.to_thread(
                        self.client.upload_part,
                        Bucket=bucket,
                        Key=key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=bytes(current_chunk_data)
                    )
                    parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
                    part_number += 1
                    current_chunk_data = bytearray()

            # Upload any remaining bytes
            if len(current_chunk_data) > 0 or not parts:
                part = await asyncio.to_thread(
                    self.client.upload_part,
                    Bucket=bucket,
                    Key=key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=bytes(current_chunk_data)
                )
                parts.append({"PartNumber": part_number, "ETag": part["ETag"]})

            # Complete Multipart Upload
            await asyncio.to_thread(
                self.client.complete_multipart_upload,
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts}
            )

            return {
                "checksum": sha256_hash.hexdigest(),
                "file_size": total_size,
                "s3_key": key,
                "s3_bucket": bucket
            }

        except Exception as e:
            # Abort multipart upload on failure
            try:
                await asyncio.to_thread(
                    self.client.abort_multipart_upload,
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id
                )
            except Exception:
                pass
            raise e

    async def generate_upload_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        await asyncio.to_thread(self._ensure_bucket_exists, bucket)
        return await asyncio.to_thread(
            self.external_client.generate_presigned_url,
            "put_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in
        )

    async def generate_download_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        return await asyncio.to_thread(
            self.external_client.generate_presigned_url,
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in
        )

    async def exists(self, bucket: str, key: str) -> bool:
        try:
            await asyncio.to_thread(
                self.client.head_object,
                Bucket=bucket,
                Key=key
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise e

    async def head(self, bucket: str, key: str) -> Dict[str, Any]:
        response = await asyncio.to_thread(
            self.client.head_object,
            Bucket=bucket,
            Key=key
        )
        return response

    async def copy(self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> None:
        await asyncio.to_thread(self._ensure_bucket_exists, dest_bucket)
        await asyncio.to_thread(
            self.client.copy_object,
            Bucket=dest_bucket,
            Key=dest_key,
            CopySource={"Bucket": src_bucket, "Key": src_key}
        )

    async def move(self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> None:
        await self.copy(src_bucket, src_key, dest_bucket, dest_key)
        await asyncio.to_thread(
            self.client.delete_object,
            Bucket=src_bucket,
            Key=src_key
        )

    async def download_stream(self, bucket: str, key: str) -> AsyncGenerator[bytes, None]:
        response = await asyncio.to_thread(
            self.client.get_object,
            Bucket=bucket,
            Key=key
        )
        body = response["Body"]
        try:
            # read chunks of 64KB
            chunk = await asyncio.to_thread(body.read, 65536)
            while chunk:
                yield chunk
                chunk = await asyncio.to_thread(body.read, 65536)
        finally:
            await asyncio.to_thread(body.close)

    def _ensure_bucket_exists(self, bucket: str) -> None:
        try:
            self.client.head_bucket(Bucket=bucket)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
                self.client.create_bucket(Bucket=bucket)
            else:
                raise e

    async def write_chunk(self, bucket: str, key: str, data: bytes) -> None:
        await asyncio.to_thread(self._ensure_bucket_exists, bucket)
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=bucket,
            Key=key,
            Body=data
        )

    async def download_object(self, bucket: str, key: str) -> bytes:
        response = await asyncio.to_thread(
            self.client.get_object,
            Bucket=bucket,
            Key=key
        )
        body = response["Body"]
        try:
            data = await asyncio.to_thread(body.read)
            return data
        finally:
            await asyncio.to_thread(body.close)

    async def merge_session_chunks(self, bucket: str, source_prefix: str, destination_key: str, expected_count: int) -> Dict[str, Any]:
        await asyncio.to_thread(self._ensure_bucket_exists, bucket)
        
        response = await asyncio.to_thread(
            self.client.list_objects_v2,
            Bucket=bucket,
            Prefix=source_prefix
        )
        contents = response.get("Contents", [])
        chunk_keys = [obj["Key"] for obj in contents if obj["Key"].endswith(".bin")]
        
        def extract_seq(key: str) -> int:
            try:
                filename = key.split("/")[-1]
                seq_part = filename.replace("chunk_", "").replace(".bin", "")
                return int(seq_part)
            except Exception:
                return 999999
        
        chunk_keys.sort(key=extract_seq)
        
        if len(chunk_keys) != expected_count:
            raise ValueError(f"Chunk count mismatch. Expected {expected_count}, found {len(chunk_keys)}")
            
        for idx, key in enumerate(chunk_keys):
            expected_num = idx + 1
            actual_num = extract_seq(key)
            if actual_num != expected_num:
                raise ValueError(f"Missing sequence number {expected_num}. Actual sequence found is {actual_num}.")

        sha256_hash = hashlib.sha256()
        total_size = 0
        
        multipart_upload = await asyncio.to_thread(
            self.client.create_multipart_upload,
            Bucket=bucket,
            Key=destination_key,
            ContentType="audio/wav"
        )
        upload_id = multipart_upload["UploadId"]
        parts = []
        part_number = 1
        current_chunk_data = bytearray()
        
        MIN_PART_SIZE = 5 * 1024 * 1024
        
        try:
            for key in chunk_keys:
                obj_resp = await asyncio.to_thread(
                    self.client.get_object,
                    Bucket=bucket,
                    Key=key
                )
                chunk_data = await asyncio.to_thread(obj_resp["Body"].read)
                current_chunk_data.extend(chunk_data)
                sha256_hash.update(chunk_data)
                total_size += len(chunk_data)
                
                if len(current_chunk_data) >= MIN_PART_SIZE:
                    part = await asyncio.to_thread(
                        self.client.upload_part,
                        Bucket=bucket,
                        Key=destination_key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=bytes(current_chunk_data)
                    )
                    parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
                    part_number += 1
                    current_chunk_data = bytearray()
            
            if len(current_chunk_data) > 0 or not parts:
                part = await asyncio.to_thread(
                    self.client.upload_part,
                    Bucket=bucket,
                    Key=destination_key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=bytes(current_chunk_data)
                )
                parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
                
            await asyncio.to_thread(
                self.client.complete_multipart_upload,
                Bucket=bucket,
                Key=destination_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts}
            )
            
            # Clean up temporary chunks
            delete_objects = [{"Key": k} for k in chunk_keys]
            await asyncio.to_thread(
                self.client.delete_objects,
                Bucket=bucket,
                Delete={"Objects": delete_objects}
            )
            
            return {
                "checksum": sha256_hash.hexdigest(),
                "file_size": total_size,
                "s3_key": destination_key,
                "s3_bucket": bucket
            }
        except Exception as err:
            try:
                await asyncio.to_thread(
                    self.client.abort_multipart_upload,
                    Bucket=bucket,
                    Key=destination_key,
                    UploadId=upload_id
                )
            except Exception:
                pass
            raise err
