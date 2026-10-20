"""Verificación de webhooks de Tupana.

Cada entrega trae los headers ``X-Pana-Event-Id``, ``X-Pana-Event-Type``,
``X-Pana-Timestamp``, ``X-Pana-Delivery`` y, si el webhook tiene ``secret``,
``X-Pana-Signature``: el HMAC SHA-256 en hexadecimal del cuerpo exacto del
request, firmado con el ``secret``. Verifica siempre contra el cuerpo crudo
(bytes tal como llegaron), nunca contra un JSON re-serializado.

La firma no incluye el timestamp: para descartar entregas repetidas usa
``X-Pana-Event-Id``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping, Optional, Union, cast

from ._errors import WebhookVerificationError
from .types import WebhookEvent

__all__ = [
    "DELIVERY_HEADER",
    "EVENT_ID_HEADER",
    "EVENT_TYPE_HEADER",
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "compute_webhook_signature",
    "construct_webhook_event",
    "verify_webhook_signature",
]

SIGNATURE_HEADER = "X-Pana-Signature"
EVENT_ID_HEADER = "X-Pana-Event-Id"
EVENT_TYPE_HEADER = "X-Pana-Event-Type"
TIMESTAMP_HEADER = "X-Pana-Timestamp"
DELIVERY_HEADER = "X-Pana-Delivery"

Payload = Union[str, bytes, bytearray, memoryview]


def _to_bytes(value: Payload) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return bytes(value)


def compute_webhook_signature(payload: Payload, secret: str) -> str:
    """Firma (HMAC SHA-256 en hex) de un payload, igual que la calcula Tupana."""
    return hmac.new(_to_bytes(secret), _to_bytes(payload), hashlib.sha256).hexdigest()


def verify_webhook_signature(payload: Payload, signature: Optional[str], secret: str) -> bool:
    """``True`` si ``signature`` corresponde al payload.

    Acepta la firma con o sin prefijo ``sha256=`` y compara en tiempo constante.
    """
    if not signature or not secret:
        return False
    received = signature.strip()
    if received.lower().startswith("sha256="):
        received = received[len("sha256=") :]
    return hmac.compare_digest(compute_webhook_signature(payload, secret), received.lower())


def _get_header(headers: Mapping[str, Any], name: str) -> Optional[str]:
    getter = getattr(headers, "get", None)
    value = getter(name) if getter else None
    if value is None:
        lowered = name.lower()
        for key, candidate in headers.items():
            if str(key).lower() == lowered:
                value = candidate
                break
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    return str(value) if value is not None else None


def construct_webhook_event(
    payload: Payload, headers: Mapping[str, Any], secret: str
) -> WebhookEvent:
    """Verifica ``X-Pana-Signature`` y devuelve el evento parseado.

    Lanza :class:`WebhookVerificationError` si la firma falta, no coincide o el
    cuerpo no es JSON.

    .. code-block:: python

        event = construct_webhook_event(await request.body(), request.headers, secret)
        if event["event"] == "document.issued":
            ...
    """
    signature = _get_header(headers, SIGNATURE_HEADER)
    if not signature:
        raise WebhookVerificationError(
            "Falta el header X-Pana-Signature. ¿Configuraste un secret en el webhook?"
        )
    if not verify_webhook_signature(payload, signature, secret):
        raise WebhookVerificationError("La firma del webhook no coincide")
    try:
        return cast(WebhookEvent, json.loads(_to_bytes(payload)))
    except ValueError as exc:
        raise WebhookVerificationError("El cuerpo del webhook no es JSON válido") from exc
