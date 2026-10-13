"""Direct-to-storage uploads: the API presigns, the phone PUTs the bytes straight to
Backblaze, then calls /complete so the server verifies size and type before use."""

import mimetypes
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import Forbidden, NotFound, ValidationFailed
from app.db.models import Upload, User
from app.domain.enums import UploadPurpose, UploadStatus
from app.integrations.storage import ObjectStorage, PresignedUpload


class UploadService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage, settings: Settings, clock: Clock) -> None:
        self._session = session
        self._storage = storage
        self._settings = settings
        self._clock = clock

    async def create(self, user: User, purpose: UploadPurpose, content_type: str) -> tuple[Upload, PresignedUpload]:
        if content_type not in self._settings.upload_allowed_types:
            raise ValidationFailed(
                "File type not allowed",
                code="content_type_not_allowed",
                details={"allowed": self._settings.upload_allowed_types},
            )
        if purpose == UploadPurpose.LISTING_PHOTO and not user.is_host:
            raise Forbidden("Only hosts can upload listing photos", code="not_a_host")
        extension = (mimetypes.guess_extension(content_type) or "").lstrip(".") or "bin"
        key = f"{purpose.value}/{user.id}/{uuid.uuid4().hex}.{extension}"
        upload = Upload(
            owner_id=user.id,
            purpose=purpose.value,
            storage_key=key,
            content_type=content_type,
            status=UploadStatus.PENDING.value,
            created_at=self._clock.now(),
        )
        self._session.add(upload)
        await self._session.commit()
        return upload, self._storage.presign_upload(key, content_type)

    async def complete(self, user: User, upload_id: uuid.UUID) -> Upload:
        upload = await self.get_owned(user, upload_id)
        if upload.status == UploadStatus.UPLOADED.value:
            return upload
        stored = await self._storage.stat(upload.storage_key)
        if stored is None:
            raise ValidationFailed("File has not been uploaded yet", code="upload_missing")
        if stored.size_bytes > self._settings.upload_max_bytes:
            await self._storage.delete(upload.storage_key)
            raise ValidationFailed(
                "File is too large", code="upload_too_large", details={"max_bytes": self._settings.upload_max_bytes}
            )
        upload.size_bytes = stored.size_bytes
        upload.status = UploadStatus.UPLOADED.value
        await self._session.commit()
        return upload

    async def get_owned(self, user: User, upload_id: uuid.UUID) -> Upload:
        upload = await self._session.get(Upload, upload_id)
        if upload is None or upload.owner_id != user.id:
            raise NotFound("Upload not found")
        return upload

    async def require_uploaded(self, user: User, upload_ids: list[uuid.UUID], purpose: UploadPurpose) -> list[Upload]:
        if not upload_ids:
            return []
        uploads = list(
            (
                await self._session.execute(
                    select(Upload).where(
                        Upload.id.in_(upload_ids),
                        Upload.owner_id == user.id,
                        Upload.purpose == purpose.value,
                        Upload.status == UploadStatus.UPLOADED.value,
                    )
                )
            ).scalars()
        )
        if len(uploads) != len(set(upload_ids)):
            raise ValidationFailed("One or more files are missing or not finished uploading", code="upload_invalid")
        order = {uid: i for i, uid in enumerate(upload_ids)}
        return sorted(uploads, key=lambda u: order[u.id])
