import asyncio
from dataclasses import dataclass
from functools import cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import Settings, get_settings


@dataclass(slots=True)
class StorageObjectMetadata:
    content_length: int | None


class StorageService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.bucket_name = self.settings.s3_bucket_name
        client_kwargs = {
            "service_name": "s3",
            "region_name": self.settings.aws_region,
            "aws_access_key_id": self.settings.aws_access_key_id,
            "aws_secret_access_key": self.settings.aws_secret_access_key,
            "config": Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        }

        if self.settings.aws_endpoint_url:
            client_kwargs["endpoint_url"] = self.settings.aws_endpoint_url

        self._client = boto3.client(
            **client_kwargs,
        )

    def _generate_presigned_upload_url(
        self,
        *,
        key: str,
        content_type: str,
        expires_in_seconds: int = 900,
    ) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in_seconds,
        )

    def _get_object_metadata(self, *, key: str) -> StorageObjectMetadata:
        response = self._client.head_object(Bucket=self.bucket_name, Key=key)
        return StorageObjectMetadata(content_length=response.get("ContentLength"))

    def _delete_object(self, *, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket_name, Key=key)

    async def generate_presigned_upload_url(
        self,
        *,
        key: str,
        content_type: str,
        expires_in_seconds: int = 900,
    ) -> str:
        return await asyncio.to_thread(
            self._generate_presigned_upload_url,
            key=key,
            content_type=content_type,
            expires_in_seconds=expires_in_seconds,
        )

    async def get_object_metadata(self, *, key: str) -> StorageObjectMetadata:
        return await asyncio.to_thread(self._get_object_metadata, key=key)

    async def delete_object(self, *, key: str) -> None:
        await asyncio.to_thread(self._delete_object, key=key)


@cache
def get_storage_service() -> StorageService:
    return StorageService()


async def object_exists(service: StorageService, *, key: str) -> bool:
    try:
        await service.get_object_metadata(key=key)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise
