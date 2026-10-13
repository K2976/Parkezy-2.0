"""Payment gateway port + Razorpay adapter. With PAYMENT_PROVIDER=offline there is no
gateway at all and bookings are paid at the venue."""

import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

import httpx

from app.core.errors import ExternalServiceError


def to_minor_units(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


@dataclass(frozen=True)
class GatewayOrder:
    provider: str
    order_id: str
    amount_minor: int
    currency: str
    public_key: str


@dataclass(frozen=True)
class GatewayPayment:
    payment_id: str
    status: str  # provider status, e.g. "captured", "failed", "authorized"
    error: str | None = None


class PaymentGateway(Protocol):
    name: str
    public_key: str

    async def create_order(self, *, amount: Decimal, currency: str, receipt: str, notes: dict) -> GatewayOrder: ...
    def verify_checkout_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool: ...
    def verify_webhook_signature(self, *, body: bytes, signature: str) -> bool: ...
    async def refund(self, *, payment_id: str, amount: Decimal) -> str: ...
    async def order_payments(self, order_id: str) -> list[GatewayPayment]: ...


def _hmac_ok(secret: str, message: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


class RazorpayGateway:
    name = "razorpay"

    def __init__(
        self, client: httpx.AsyncClient, api_base: str, key_id: str, key_secret: str, webhook_secret: str
    ) -> None:
        self._client = client
        self._base = api_base.rstrip("/")
        self._key_id = key_id
        self.public_key = key_id
        self._key_secret = key_secret
        self._webhook_secret = webhook_secret

    async def _post(self, path: str, body: dict) -> dict:
        try:
            response = await self._client.post(f"{self._base}{path}", json=body, auth=(self._key_id, self._key_secret))
        except httpx.HTTPError as e:
            raise ExternalServiceError("Payment provider unreachable") from e
        if response.status_code >= 400:
            raise ExternalServiceError(
                "Payment provider error", details={"status": response.status_code, "body": response.text[:500]}
            )
        return response.json()

    async def create_order(self, *, amount: Decimal, currency: str, receipt: str, notes: dict) -> GatewayOrder:
        data = await self._post(
            "/orders",
            {"amount": to_minor_units(amount), "currency": currency, "receipt": receipt[:40], "notes": notes},
        )
        return GatewayOrder(
            provider=self.name,
            order_id=data["id"],
            amount_minor=int(data["amount"]),
            currency=data["currency"],
            public_key=self._key_id,
        )

    def verify_checkout_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        return _hmac_ok(self._key_secret, f"{order_id}|{payment_id}".encode(), signature)

    def verify_webhook_signature(self, *, body: bytes, signature: str) -> bool:
        return _hmac_ok(self._webhook_secret, body, signature)

    async def order_payments(self, order_id: str) -> list[GatewayPayment]:
        """Source of truth for reconciliation: what the PSP actually recorded for an order."""
        try:
            response = await self._client.get(
                f"{self._base}/orders/{order_id}/payments", auth=(self._key_id, self._key_secret)
            )
        except httpx.HTTPError as e:
            raise ExternalServiceError("Payment provider unreachable") from e
        if response.status_code >= 400:
            raise ExternalServiceError("Payment provider error", details={"status": response.status_code})
        return [
            GatewayPayment(payment_id=p["id"], status=p["status"], error=p.get("error_description"))
            for p in response.json().get("items", [])
        ]

    async def refund(self, *, payment_id: str, amount: Decimal) -> str:
        data = await self._post(f"/payments/{payment_id}/refund", {"amount": to_minor_units(amount)})
        return str(data["id"])
