"""Lógica compartida por el cliente síncrono y el asíncrono."""

from __future__ import annotations

import email.utils
import os
import random
import time
import uuid
from typing import Any, Dict, Mapping, Optional, Sequence, Union

import httpx

from ._errors import TupanaError
from ._version import __version__

DEFAULT_BASE_URL = "https://api.tupana.ai/v2"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2

#: Status que justifican reintentar.
RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})
#: Status donde el servidor garantiza que el request NO se procesó.
NOT_PROCESSED_STATUS = frozenset({429, 503})

QueryValue = Union[str, int, float, bool, None, Sequence[Union[str, int]]]
Query = Mapping[str, QueryValue]


def random_idempotency_key() -> str:
    """UUID v4 para el header ``Idempotency-Key``."""
    return str(uuid.uuid4())


def resolve_api_key(api_key: Optional[str]) -> str:
    key = api_key or os.environ.get("TUPANA_API_KEY", "").strip()
    if not key:
        raise TupanaError(
            "Falta la API key: pásala como Tupana(api_key=...) o define TUPANA_API_KEY."
        )
    return key


def resolve_base_url(base_url: Optional[str]) -> str:
    url = base_url or os.environ.get("TUPANA_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return url.rstrip("/")


def clean_query(query: Optional[Query]) -> Dict[str, Any]:
    """Quita ``None`` y une listas con coma (``dte_type__code__in=33,34``)."""
    out: Dict[str, Any] = {}
    for key, value in (query or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, (list, tuple)):
            if value:
                out[key] = ",".join(str(v) for v in value)
        else:
            out[key] = value
    return out


def path_id(value: Union[str, int]) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("El id no puede estar vacío")
    from urllib.parse import quote

    return quote(text, safe="")


def build_headers(
    api_key: str,
    default_headers: Optional[Mapping[str, str]],
    *,
    has_body: bool,
    idempotency_key: Optional[str],
    use_defaults: Optional[bool],
    extra: Optional[Mapping[str, str]],
) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Accept": "application/json",
        "Authorization": f"Api-Key {api_key}",
        "User-Agent": f"tupana-python/{__version__}",
        "X-Tupana-SDK": f"python/{__version__}",
    }
    headers.update(default_headers or {})
    if has_body:
        headers["Content-Type"] = "application/json"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    if use_defaults is not None:
        headers["X-Use-Defaults"] = "true" if use_defaults else "false"
    headers.update(extra or {})
    return headers


def can_retry(method: str, idempotency_key: Optional[str], status: Optional[int]) -> bool:
    """Decide si un intento fallido se puede repetir sin riesgo de duplicar.

    - ``GET``/``PUT``/``DELETE`` o requests con ``Idempotency-Key``: ante error de
      red, 408, 429 y 5xx.
    - ``POST``/``PATCH`` sin key: solo ante 429 y 503 (el servidor no lo procesó).
    """
    idempotent = method in ("GET", "PUT", "DELETE") or bool(idempotency_key)
    if status is None:
        return idempotent
    if status in NOT_PROCESSED_STATUS:
        return True
    return idempotent and status in RETRYABLE_STATUS


def retry_delay(attempt: int, headers: Optional[httpx.Headers] = None) -> float:
    """Backoff exponencial con jitter; respeta ``Retry-After`` (segundos o fecha)."""
    retry_after = headers.get("retry-after") if headers is not None else None
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 60.0)
        except ValueError:
            parsed = email.utils.parsedate_to_datetime(retry_after)
            if parsed is not None:
                return min(max(parsed.timestamp() - time.time(), 0.0), 60.0)
    base: float = min(0.5 * (2**attempt), 8.0)
    return base + base * 0.25 * random.random()


def parse_response(response: httpx.Response) -> Any:
    if response.status_code == 204 or not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text
