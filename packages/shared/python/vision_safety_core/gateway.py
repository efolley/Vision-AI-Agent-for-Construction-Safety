from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Protocol


class GatewayError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    tenant_id: str
    role: str


class JwtVerifier:
    def __init__(self, secret: str, issuer: str, audience: str) -> None:
        self.secret, self.issuer, self.audience = secret, issuer, audience

    def verify(self, token: str) -> Principal:
        try:
            header, payload, signature = token.split(".")
            expected = _b64(
                hmac.new(
                    self.secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256
                ).digest()
            )
            claims = json.loads(_unb64(payload))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GatewayError("Malformed token") from error
        if not hmac.compare_digest(expected, signature):
            raise GatewayError("Invalid token signature")
        if (
            claims.get("iss") != self.issuer
            or claims.get("aud") != self.audience
            or claims.get("exp", 0) <= time.time()
        ):
            raise GatewayError("Invalid token claims")
        if not all(isinstance(claims.get(key), str) for key in ("sub", "tenant_id", "role")):
            raise GatewayError("Missing token claims")
        return Principal(claims["sub"], claims["tenant_id"], claims["role"])

    def issue_for_test(self, principal: Principal, expires_at: float | None = None) -> str:
        payload = {
            "sub": principal.subject,
            "tenant_id": principal.tenant_id,
            "role": principal.role,
            "iss": self.issuer,
            "aud": self.audience,
            "exp": expires_at or time.time() + 3600,
        }
        header = _b64(b'{"alg":"HS256","typ":"JWT"}')
        encoded = _b64(json.dumps(payload).encode())
        sig = _b64(
            hmac.new(self.secret.encode(), f"{header}.{encoded}".encode(), hashlib.sha256).digest()
        )
        return f"{header}.{encoded}.{sig}"


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> str:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()


class KeyValueStore(Protocol):
    def set(self, key: str, value: str, *, nx: bool, ex: int) -> bool: ...


class InMemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, float] = {}

    def set(self, key: str, value: str, *, nx: bool, ex: int) -> bool:
        now = time.monotonic()
        self.values = {k: v for k, v in self.values.items() if v > now}
        if nx and key in self.values:
            return False
        self.values[key] = now + ex
        return True


class RateLimiter:
    def __init__(self, store: KeyValueStore, limit: int, window_seconds: int) -> None:
        self.store, self.limit, self.window_seconds, self.counts = store, limit, window_seconds, {}

    def allow(self, tenant_id: str) -> bool:
        now = int(time.time() // self.window_seconds)
        key = f"rate:{tenant_id}:{now}"
        count = self.counts.get(key, 0)
        if count >= self.limit:
            return False
        if self.store.set(f"{key}:{count}", "1", nx=True, ex=self.window_seconds):
            self.counts[key] = count + 1
            return True
        return False


class IdempotencyService:
    def __init__(self, store: KeyValueStore, ttl_seconds: int = 86400) -> None:
        self.store, self.ttl_seconds = store, ttl_seconds

    def claim(self, tenant_id: str, key: str) -> bool:
        return self.store.set(
            f"idempotency:{tenant_id}:{key}", "claimed", nx=True, ex=self.ttl_seconds
        )
