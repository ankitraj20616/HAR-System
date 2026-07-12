"""Short-lived, one-time tickets used for browser WebSocket handshakes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Literal

from services.auth_service.models import AuthenticatedUser


class InvalidTicket(ValueError):
    pass


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass
class TicketManager:
    secret: str
    ttl_seconds: int
    _used_nonces: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def issue(self, user: AuthenticatedUser, target: Literal["fusion", "feedback"]) -> str:
        payload = {
            "exp": int(time.time()) + self.ttl_seconds,
            "nonce": secrets.token_urlsafe(18),
            "role": user.role,
            "sub": user.user_id,
            "target": target,
        }
        encoded = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        signature = hmac.new(self.secret.encode(), encoded.encode(), hashlib.sha256).digest()
        return f"{encoded}.{_encode(signature)}"

    def consume(self, ticket: str, target: Literal["fusion", "feedback"]) -> dict[str, str]:
        try:
            encoded, supplied_signature = ticket.split(".", 1)
            expected = hmac.new(self.secret.encode(), encoded.encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _decode(supplied_signature)):
                raise InvalidTicket("ticket signature is invalid")
            payload = json.loads(_decode(encoded))
            now = int(time.time())
            if int(payload["exp"]) < now or payload["target"] != target:
                raise InvalidTicket("ticket is expired or has the wrong target")
            nonce = str(payload["nonce"])
            with self._lock:
                self._used_nonces = {
                    key: exp for key, exp in self._used_nonces.items() if exp >= now
                }
                if nonce in self._used_nonces:
                    raise InvalidTicket("ticket was already used")
                self._used_nonces[nonce] = int(payload["exp"])
            return {"sub": str(payload["sub"]), "role": str(payload["role"])}
        except InvalidTicket:
            raise
        except Exception as exc:
            raise InvalidTicket("ticket is malformed") from exc
