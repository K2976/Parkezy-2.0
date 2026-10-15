"""Keyset pagination cursors: an opaque (timestamp, id) pair, newest first.

Stable under inserts (no skipped or repeated rows, unlike OFFSET) and index-friendly."""

import base64
import uuid
from datetime import datetime

from app.core.errors import ValidationFailed


def encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{row_id}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        created, rid = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(created), uuid.UUID(rid)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValidationFailed("Invalid cursor", code="invalid_cursor") from e


def page[T](rows: list[T], limit: int, key) -> tuple[list[T], str | None]:
    """Split a `limit + 1` query result into the page and the cursor for the next one."""
    if len(rows) <= limit:
        return rows, None
    created_at, row_id = key(rows[limit - 1])
    return rows[:limit], encode_cursor(created_at, row_id)
