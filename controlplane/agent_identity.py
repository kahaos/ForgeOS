"""Development agent authentication using request-bound HMAC assertions."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable


def _canonical(value: dict[str, str]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AgentAssertion:
    agent_id: str
    audience: str
    request_digest: str
    issued_at: str
    expires_at: str
    nonce: str
    signature: str

    def unsigned_dict(self) -> dict[str, str]:
        data = asdict(self)
        data.pop("signature", None)
        return data


class AgentAuthenticator:
    """Authenticate agents by proving possession of a provisioned secret.

    Secrets are intentionally process-local in this prototype. Production
    key management will move the trust anchor into a dedicated credential
    system and should prefer sender-constrained/asymmetric credentials.
    """

    def __init__(
        self,
        *,
        ttl_seconds: int = 60,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self.clock = clock or _now
        self._secrets: dict[str, bytes] = {}
        self._consumed: set[str] = set()

    def register(self, agent_id: str, secret: bytes) -> None:
        if not agent_id:
            raise ValueError("agent_id is required")
        if len(secret) < 16:
            raise ValueError("agent secret must be at least 16 bytes")
        self._secrets[agent_id] = bytes(secret)

    def sign_request(
        self,
        agent_id: str,
        secret: bytes,
        *,
        request_digest: str,
        audience: str,
    ) -> AgentAssertion:
        registered = self._secrets.get(agent_id)
        if registered is None or not hmac.compare_digest(registered, bytes(secret)):
            raise ValueError("authentication failed")
        if not request_digest:
            raise ValueError("request_digest is required")
        if not audience:
            raise ValueError("audience is required")

        issued = self.clock().astimezone(timezone.utc)
        expires = issued + timedelta(seconds=self.ttl_seconds)
        assertion = AgentAssertion(
            agent_id=agent_id,
            audience=audience,
            request_digest=request_digest,
            issued_at=issued.isoformat(),
            expires_at=expires.isoformat(),
            nonce=secrets.token_hex(32),
            signature="",
        )
        signature = hmac.new(
            registered,
            _canonical(assertion.unsigned_dict()),
            hashlib.sha256,
        ).hexdigest()
        return AgentAssertion(**{**asdict(assertion), "signature": signature})

    def verify(
        self,
        assertion: AgentAssertion,
        *,
        request_digest: str,
        audience: str,
    ) -> str:
        secret = self._secrets.get(assertion.agent_id)
        if secret is None:
            raise ValueError("unknown agent")

        expected = hmac.new(
            secret,
            _canonical(assertion.unsigned_dict()),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, assertion.signature):
            raise ValueError("signature mismatch")
        if assertion.request_digest != request_digest:
            raise ValueError("request digest mismatch")
        if assertion.audience != audience:
            raise ValueError("audience mismatch")

        try:
            expires = datetime.fromisoformat(assertion.expires_at).astimezone(timezone.utc)
        except ValueError as exc:
            raise ValueError("invalid assertion expiry") from exc
        if self.clock().astimezone(timezone.utc) >= expires:
            raise ValueError("assertion expired")

        if assertion.nonce in self._consumed:
            raise ValueError("assertion already consumed")
        self._consumed.add(assertion.nonce)
        return assertion.agent_id
