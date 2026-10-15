from typing import Any

from pydantic import BaseModel, ConfigDict


def find_nul(value: Any, path: str = "") -> str | None:
    """Location of the first string (or dict key) containing U+0000, or None."""
    if isinstance(value, str):
        return path or "value" if "\x00" in value else None
    if isinstance(value, dict):
        for key, item in value.items():
            here = f"{path}.{key}" if path else str(key)
            if isinstance(key, str) and "\x00" in key:
                return here
            found = find_nul(item, here)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            found = find_nul(item, f"{path}[{i}]")
            if found:
                return found
    return None


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class Page[T](Schema):
    items: list[T]
    next_cursor: str | None = None


class Message(Schema):
    message: str
