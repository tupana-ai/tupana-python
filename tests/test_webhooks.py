from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from tupana import (
    Tupana,
    WebhookVerificationError,
    compute_webhook_signature,
    construct_webhook_event,
    verify_webhook_signature,
)

SECRET = "whsec_test"
BODY = json.dumps(
    {"event": "document.issued", "created_at": "2026-10-20T10:00:00Z", "data": {"id": "docu_1"}}
)
# Así firma el backend de Tupana: hmac.new(secret, body, sha256).hexdigest()
SIGNATURE = hmac.new(SECRET.encode(), BODY.encode(), hashlib.sha256).hexdigest()


def test_compute_matches_backend() -> None:
    assert compute_webhook_signature(BODY, SECRET) == SIGNATURE
    assert compute_webhook_signature(BODY.encode(), SECRET) == SIGNATURE


def test_verify_accepts_valid_signatures() -> None:
    assert verify_webhook_signature(BODY, SIGNATURE, SECRET)
    assert verify_webhook_signature(BODY.encode(), f"sha256={SIGNATURE}", SECRET)
    assert verify_webhook_signature(BODY, SIGNATURE.upper(), SECRET)


def test_verify_rejects_invalid_signatures() -> None:
    assert not verify_webhook_signature(BODY + " ", SIGNATURE, SECRET)
    assert not verify_webhook_signature(BODY, "", SECRET)
    assert not verify_webhook_signature(BODY, None, SECRET)
    assert not verify_webhook_signature(BODY, SIGNATURE, "otro")


def test_construct_event() -> None:
    event = construct_webhook_event(BODY, {"x-pana-signature": SIGNATURE}, SECRET)
    assert event["event"] == "document.issued"
    event = construct_webhook_event(BODY.encode(), {"X-Pana-Signature": [SIGNATURE]}, SECRET)
    assert event["data"] == {"id": "docu_1"}


def test_construct_event_errors() -> None:
    with pytest.raises(WebhookVerificationError):
        construct_webhook_event(BODY, {}, SECRET)
    with pytest.raises(WebhookVerificationError):
        construct_webhook_event(BODY, {"X-Pana-Signature": "00"}, SECRET)
    bad = "no-json"
    with pytest.raises(WebhookVerificationError):
        construct_webhook_event(
            bad, {"X-Pana-Signature": compute_webhook_signature(bad, SECRET)}, SECRET
        )


def test_client_helpers() -> None:
    client = Tupana("k")
    sig = client.webhooks.sign(BODY, SECRET)
    assert sig == SIGNATURE
    assert (
        client.webhooks.unwrap(BODY, {"X-Pana-Signature": sig}, SECRET)["event"]
        == "document.issued"
    )
