import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.errors import ExternalServiceError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PushMessage:
    tokens: list[str]
    title: str
    body: str
    data: dict


class PushSender(Protocol):
    async def send(self, message: PushMessage) -> list[str]:
        """Send and return tokens the provider reported as no longer valid."""
        ...


class ExpoPushSender:
    BATCH = 100  # Expo accepts at most 100 messages per request

    def __init__(self, client: httpx.AsyncClient, url: str, access_token: str | None) -> None:
        self._client = client
        self._url = url
        self._headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if access_token:
            self._headers["Authorization"] = f"Bearer {access_token}"

    async def send(self, message: PushMessage) -> list[str]:
        invalid: list[str] = []
        for i in range(0, len(message.tokens), self.BATCH):
            batch = message.tokens[i : i + self.BATCH]
            payload = [
                {"to": t, "title": message.title, "body": message.body, "data": message.data, "sound": "default"}
                for t in batch
            ]
            try:
                response = await self._client.post(self._url, json=payload, headers=self._headers)
            except httpx.HTTPError as e:
                raise ExternalServiceError("Push provider unreachable") from e
            if response.status_code >= 400:
                raise ExternalServiceError("Push provider error", details={"status": response.status_code})
            for token, ticket in zip(batch, response.json().get("data", []), strict=False):
                if ticket.get("details", {}).get("error") == "DeviceNotRegistered":
                    invalid.append(token)
        return invalid


class NoopPushSender:
    async def send(self, message: PushMessage) -> list[str]:
        log.debug("push disabled; dropping %s", message.title)
        return []
