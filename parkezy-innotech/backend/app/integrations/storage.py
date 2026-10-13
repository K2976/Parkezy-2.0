"""Object storage over the S3 API (Backblaze B2 in production, SeaweedFS locally)."""

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.errors import ExternalServiceError


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    method: str
    headers: dict[str, str]
    expires_in: int


@dataclass(frozen=True)
class StoredObject:
    size_bytes: int
    content_type: str | None


class ObjectStorage(Protocol):
    def presign_upload(self, key: str, content_type: str) -> PresignedUpload: ...
    def download_url(self, key: str) -> str: ...
    async def stat(self, key: str) -> StoredObject | None: ...
    async def delete(self, key: str) -> None: ...


class S3ObjectStorage:
    def __init__(
        self,
        *,
        endpoint_url: str,
        public_endpoint_url: str | None,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        presign_ttl_seconds: int,
        public_base_url: str | None,
    ) -> None:
        def client(endpoint: str):
            return boto3.client(
                "s3",
                endpoint_url=endpoint,
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )

        self._client = client(endpoint_url)
        # Presigned URLs embed the host, so sign with the endpoint the phone can reach.
        self._signer = client(public_endpoint_url) if public_endpoint_url else self._client
        self._bucket = bucket
        self._ttl = presign_ttl_seconds
        self._public_base_url = public_base_url.rstrip("/") if public_base_url else None
        # Signing is CPU work (~0.1 ms each); search results can carry hundreds of photos.
        # Reuse a signed URL for half its lifetime so clients never receive an almost-expired one.
        self._signed: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._signed_max = 20_000

    def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        url = self._signer.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=self._ttl,
        )
        return PresignedUpload(url=url, method="PUT", headers={"Content-Type": content_type}, expires_in=self._ttl)

    def download_url(self, key: str) -> str:
        if self._public_base_url:
            return f"{self._public_base_url}/{key}"
        now = time.monotonic()
        cached = self._signed.get(key)
        if cached and cached[1] > now:
            self._signed.move_to_end(key)
            return cached[0]
        url = self._signer.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=self._ttl
        )
        self._signed[key] = (url, now + self._ttl / 2)
        if len(self._signed) > self._signed_max:
            self._signed.popitem(last=False)
        return url

    async def stat(self, key: str) -> StoredObject | None:
        def head():
            return self._client.head_object(Bucket=self._bucket, Key=key)

        try:
            meta = await asyncio.to_thread(head)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None
            raise ExternalServiceError("Storage unavailable") from e
        except BotoCoreError as e:
            raise ExternalServiceError("Storage unavailable") from e
        return StoredObject(size_bytes=int(meta["ContentLength"]), content_type=meta.get("ContentType"))

    async def delete(self, key: str) -> None:
        try:
            await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)
        except (ClientError, BotoCoreError) as e:
            raise ExternalServiceError("Storage unavailable") from e

    async def ensure_bucket(self) -> None:
        """Development helper; production buckets are created in the B2 console."""

        def create():
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError:
                self._client.create_bucket(Bucket=self._bucket)

        await asyncio.to_thread(create)
