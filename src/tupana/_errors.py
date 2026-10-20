"""Errores tipados del SDK.

La API v2 responde los errores con un envelope estilo Stripe::

    {"error": {"type", "code", "message", "param?", "resource?", "doc_url?", "request_id"}}

Algunos endpoints todavía usan formatos planos (``{"error": "..."}``,
``{"error_code", "message"}`` o el diccionario de validación de DRF). El SDK
los normaliza todos en :class:`APIError`.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx

__all__ = [
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequestError",
    "BatchTimeoutError",
    "ConflictError",
    "InternalServerError",
    "NotFoundError",
    "PayloadTooLargeError",
    "PermissionDeniedError",
    "RateLimitError",
    "TupanaError",
    "UnprocessableEntityError",
    "WebhookVerificationError",
]


class TupanaError(Exception):
    """Base de todos los errores del SDK."""


class APIError(TupanaError):
    """La API respondió con un status HTTP no exitoso."""

    status_code: int
    type: Optional[str]
    code: Optional[str]
    param: Optional[str]
    doc_url: Optional[str]
    request_id: Optional[str]
    body: Any
    response: httpx.Response

    def __init__(self, message: str, *, response: httpx.Response, body: Any) -> None:
        super().__init__(message)
        self.message = message
        self.response = response
        self.status_code = response.status_code
        self.body = body
        parsed = normalize_error_body(body)
        self.type = parsed.get("type")
        self.code = parsed.get("code")
        self.param = parsed.get("param")
        self.doc_url = parsed.get("doc_url")
        self.request_id = parsed.get("request_id") or response.headers.get("x-request-id")

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status_code={self.status_code}, code={self.code!r}, "
            f"message={self.message!r}, request_id={self.request_id!r})"
        )


class BadRequestError(APIError):
    pass


class AuthenticationError(APIError):
    pass


class PermissionDeniedError(APIError):
    pass


class NotFoundError(APIError):
    pass


class ConflictError(APIError):
    pass


class PayloadTooLargeError(APIError):
    pass


class UnprocessableEntityError(APIError):
    pass


class RateLimitError(APIError):
    pass


class InternalServerError(APIError):
    pass


class APIConnectionError(TupanaError):
    """No se pudo conectar con la API (DNS, TLS, conexión cortada…)."""

    def __init__(self, message: str = "No se pudo conectar con la API de Tupana") -> None:
        super().__init__(message)


class APITimeoutError(APIConnectionError):
    """El request superó el timeout configurado."""

    def __init__(self, message: str = "El request a la API de Tupana superó el timeout") -> None:
        super().__init__(message)


class WebhookVerificationError(TupanaError):
    """La firma del webhook falta, no coincide o el cuerpo no es JSON."""


class BatchTimeoutError(TupanaError):
    """``wait_for_batch`` superó su tiempo máximo de espera."""

    def __init__(self, batch_id: str, last_status: Any) -> None:
        super().__init__(f"El lote {batch_id} no terminó dentro del tiempo de espera")
        self.batch_id = batch_id
        self.last_status = last_status


_STATUS_TO_ERROR: Dict[int, type[APIError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    413: PayloadTooLargeError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}


def _as_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def normalize_error_body(body: Any) -> Dict[str, Any]:
    """Normaliza cualquiera de los formatos de error de la API."""
    if isinstance(body, str):
        return {"message": body} if body else {}
    if not isinstance(body, dict):
        return {}
    error = body.get("error")
    if isinstance(error, dict):
        return error
    message = _as_str(error) or _as_str(body.get("message")) or _as_str(body.get("detail"))
    code = _as_str(body.get("code")) or _as_str(body.get("error_code"))
    if message or code:
        return {"message": message, "code": code}
    for field, value in body.items():
        text = " ".join(map(str, value)) if isinstance(value, list) else json.dumps(value)
        return {"message": f"{field}: {text}", "param": field, "type": "validation_error"}
    return {}


def make_api_error(response: httpx.Response) -> APIError:
    """Construye la subclase adecuada para la respuesta."""
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text
    parsed = normalize_error_body(body)
    message = parsed.get("message") or f"La API respondió {response.status_code}"
    cls = _STATUS_TO_ERROR.get(response.status_code)
    if cls is None:
        cls = InternalServerError if response.status_code >= 500 else APIError
    return cls(message, response=response, body=body)
