from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from controlplane.agent_identity import AgentAuthenticator


KEY = b"agent-identity-test-secret-32-bytes-long"


def test_authenticated_agent_request_binds_identity_and_request():
    now = datetime(2026, 10, 3, 13, 0, tzinfo=timezone.utc)
    auth = AgentAuthenticator(clock=lambda: now)
    auth.register("agent-1", KEY)

    assertion = auth.sign_request("agent-1", KEY, request_digest="digest-123", audience="forgeos")

    assert auth.verify(assertion, request_digest="digest-123", audience="forgeos") == "agent-1"


def test_wrong_secret_cannot_create_valid_assertion():
    now = datetime(2026, 10, 3, 13, 0, tzinfo=timezone.utc)
    auth = AgentAuthenticator(clock=lambda: now)
    auth.register("agent-1", KEY)

    with pytest.raises(ValueError, match="authentication failed"):
        auth.sign_request("agent-1", b"wrong-secret", request_digest="digest-123", audience="forgeos")


def test_request_digest_tampering_is_rejected():
    now = datetime(2026, 10, 3, 13, 0, tzinfo=timezone.utc)
    auth = AgentAuthenticator(clock=lambda: now)
    auth.register("agent-1", KEY)
    assertion = auth.sign_request("agent-1", KEY, request_digest="digest-123", audience="forgeos")

    with pytest.raises(ValueError, match="request digest mismatch"):
        auth.verify(assertion, request_digest="different", audience="forgeos")


def test_audience_substitution_is_rejected():
    now = datetime(2026, 10, 3, 13, 0, tzinfo=timezone.utc)
    auth = AgentAuthenticator(clock=lambda: now)
    auth.register("agent-1", KEY)
    assertion = auth.sign_request("agent-1", KEY, request_digest="digest-123", audience="forgeos")

    with pytest.raises(ValueError, match="audience mismatch"):
        auth.verify(assertion, request_digest="digest-123", audience="other-service")


def test_expired_assertion_is_rejected():
    issued = datetime(2026, 10, 3, 13, 0, tzinfo=timezone.utc)
    auth = AgentAuthenticator(clock=lambda: issued, ttl_seconds=30)
    auth.register("agent-1", KEY)
    assertion = auth.sign_request("agent-1", KEY, request_digest="digest-123", audience="forgeos")

    auth.clock = lambda: issued + timedelta(seconds=31)
    with pytest.raises(ValueError, match="assertion expired"):
        auth.verify(assertion, request_digest="digest-123", audience="forgeos")


def test_assertion_replay_is_rejected():
    now = datetime(2026, 10, 3, 13, 0, tzinfo=timezone.utc)
    auth = AgentAuthenticator(clock=lambda: now)
    auth.register("agent-1", KEY)
    assertion = auth.sign_request("agent-1", KEY, request_digest="digest-123", audience="forgeos")

    assert auth.verify(assertion, request_digest="digest-123", audience="forgeos") == "agent-1"
    with pytest.raises(ValueError, match="assertion already consumed"):
        auth.verify(assertion, request_digest="digest-123", audience="forgeos")


def test_signature_tampering_is_rejected():
    now = datetime(2026, 10, 3, 13, 0, tzinfo=timezone.utc)
    auth = AgentAuthenticator(clock=lambda: now)
    auth.register("agent-1", KEY)
    assertion = auth.sign_request("agent-1", KEY, request_digest="digest-123", audience="forgeos")

    with pytest.raises(ValueError, match="signature mismatch"):
        auth.verify(replace(assertion, signature="bad"), request_digest="digest-123", audience="forgeos")
