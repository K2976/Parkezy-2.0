from typing import Protocol


class JobQueue(Protocol):
    """Port for background work. Celery implements it in production; tests use a fake."""

    def enqueue(self, task: str, *args: object, countdown_seconds: int | None = None) -> None: ...
