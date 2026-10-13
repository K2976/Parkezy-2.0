from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class Page[T](Schema):
    items: list[T]
    next_cursor: str | None = None


class Message(Schema):
    message: str
