"""Email delivery. Services depend on the `EmailSender` protocol only; the concrete
provider is chosen from EMAIL_PROVIDER in app/container.py."""

import asyncio
import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage
from email.utils import make_msgid
from pathlib import Path
from typing import Protocol

import httpx
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.core.errors import ExternalServiceError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    html: str
    text: str
    idempotency_key: str
    tags: dict[str, str] = field(default_factory=dict)


class EmailSender(Protocol):
    async def send(self, email: OutgoingEmail) -> str:
        """Deliver and return the provider message id. Raise ExternalServiceError on retryable
        failure, PermanentEmailError when retrying the same message can never succeed."""
        ...


class PermanentEmailError(ExternalServiceError):
    """The provider rejected this message for good (bad recipient, invalid payload…). Retrying is pointless."""


# Resend errors worth retrying (https://resend.com/docs/api-reference/errors). 401/403 are config
# problems (bad key, unverified domain) an operator can fix, so they stay retryable within the
# outbox's bounded attempts; other 4xx are permanent for this message.
RESEND_RETRYABLE_STATUS = {401, 403, 429}
RESEND_RETRYABLE_409 = {"concurrent_idempotent_requests", "resource_locked"}


class ResendEmailSender:
    def __init__(
        self, client: httpx.AsyncClient, api_base: str, api_key: str, sender: str, reply_to: str | None
    ) -> None:
        self._client = client
        self._url = f"{api_base.rstrip('/')}/emails"
        self._api_key = api_key
        self._sender = sender
        self._reply_to = reply_to

    async def send(self, email: OutgoingEmail) -> str:
        body: dict = {
            "from": self._sender,
            "to": [email.to],
            "subject": email.subject,
            "html": email.html,
            "text": email.text,
            "tags": [{"name": k, "value": v} for k, v in email.tags.items()],
        }
        if self._reply_to:
            body["reply_to"] = self._reply_to
        try:
            response = await self._client.post(
                self._url,
                json=body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Idempotency-Key": email.idempotency_key[:256],
                },
            )
        except httpx.HTTPError as e:
            raise ExternalServiceError("Email provider unreachable", details={"error": type(e).__name__}) from e
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        status = response.status_code
        if status >= 400:
            # Resend's error body is {statusCode, name, message}; never echo our request (it holds codes).
            name = str(payload.get("name", ""))
            details = {"status": status, "name": name, "message": str(payload.get("message", ""))[:300]}
            retryable = status >= 500 or status in RESEND_RETRYABLE_STATUS or name in RESEND_RETRYABLE_409
            error = ExternalServiceError if retryable else PermanentEmailError
            raise error("Email provider rejected the message", code=name or None, details=details)
        message_id = payload.get("id")
        if not message_id:
            # Retrying is safe: the Idempotency-Key makes Resend return the original result.
            raise ExternalServiceError("Email provider returned no message id", details={"status": status})
        return str(message_id)


class SmtpEmailSender:
    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        reply_to: str | None,
        username: str | None,
        password: str | None,
        use_tls: bool,
        timeout: float,
    ) -> None:
        self._host, self._port = host, port
        self._sender, self._reply_to = sender, reply_to
        self._username, self._password = username, password
        self._use_tls, self._timeout = use_tls, timeout

    def _send_sync(self, email: OutgoingEmail) -> str:
        message = MimeMessage()
        message_id = make_msgid(domain="parkezy.local")
        message["Message-ID"] = message_id
        message["From"] = self._sender
        message["To"] = email.to
        message["Subject"] = email.subject
        if self._reply_to:
            message["Reply-To"] = self._reply_to
        message.set_content(email.text)
        message.add_alternative(email.html, subtype="html")
        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username and self._password:
                smtp.login(self._username, self._password)
            smtp.send_message(message)
        return message_id

    async def send(self, email: OutgoingEmail) -> str:
        try:
            return await asyncio.to_thread(self._send_sync, email)
        except (OSError, smtplib.SMTPException) as e:
            raise ExternalServiceError("SMTP delivery failed") from e


class ConsoleEmailSender:
    async def send(self, email: OutgoingEmail) -> str:
        log.info("EMAIL to=%s subject=%s\n%s", email.to, email.subject, email.text)
        return f"console-{email.idempotency_key}"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


class EmailRenderer:
    """Jinja templates in app/templates/emails/<name>.{subject,html,txt}."""

    def __init__(self, template_dir: Path, globals_: dict) -> None:
        self._env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html"]),
            undefined=StrictUndefined,
        )
        self._env.globals.update(globals_)

    def render(self, template: str, context: dict) -> RenderedEmail:
        return RenderedEmail(
            subject=self._env.get_template(f"{template}.subject").render(context).strip(),
            html=self._env.get_template(f"{template}.html").render(context),
            text=self._env.get_template(f"{template}.txt").render(context),
        )

    def has(self, template: str) -> bool:
        return f"{template}.html" in self._env.list_templates()
