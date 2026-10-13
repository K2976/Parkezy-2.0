import base64
import hashlib
import hmac
from datetime import datetime


def verify_svix_signature(
    *,
    secret: str,
    msg_id: str,
    timestamp: str,
    signature_header: str,
    body: bytes,
    now: datetime,
    tolerance_seconds: int = 300,
) -> bool:
    """Resend signs webhooks with Svix: base64(HMAC-SHA256(secret, f"{id}.{ts}.{body}"))."""
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(now.timestamp() - sent_at) > tolerance_seconds:
        return False
    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"{msg_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    for part in signature_header.split():
        version, _, sig = part.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            return True
    return False
