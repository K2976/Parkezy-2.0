import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import Schema


def _blank_to_none(v: str | None) -> str | None:
    return v or None  # whitespace is already stripped by Schema


class ReviewCreate(Schema):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)

    _c = field_validator("comment")(_blank_to_none)


class ReviewUpdate(Schema):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewReply(Schema):
    reply: str = Field(min_length=1, max_length=1000)


class ReviewAuthor(Schema):
    first_name: str


class ReviewOut(Schema):
    id: uuid.UUID
    booking_id: uuid.UUID
    listing_id: uuid.UUID
    rating: int
    comment: str | None
    author: ReviewAuthor
    host_reply: str | None
    host_replied_at: datetime | None
    created_at: datetime
    updated_at: datetime
