"""Clientes síncrono (:class:`Tupana`) y asíncrono (:class:`AsyncTupana`)."""

from __future__ import annotations

import asyncio
import time
from types import TracebackType
from typing import Any, Mapping, Optional, Type, Union

import httpx

from ._base import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    Query,
    build_headers,
    can_retry,
    clean_query,
    parse_response,
    resolve_api_key,
    resolve_base_url,
    retry_delay,
)
from ._errors import APIConnectionError, APITimeoutError, make_api_error
from .resources.cessions import AsyncCessions, Cessions
from .resources.connections import (
    AsyncConnections,
    AsyncMasterEntities,
    Connections,
    MasterEntities,
)
from .resources.documents import AsyncDocuments, Documents
from .resources.payment_requests import AsyncPaymentRequests, PaymentRequests
from .resources.webhooks import AsyncWebhooks, Webhooks

__all__ = ["AsyncTupana", "Tupana"]


class _Config:
    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: float,
        max_retries: int,
        default_headers: Optional[Mapping[str, str]],
    ) -> None:
        self.api_key = resolve_api_key(api_key)
        self.base_url = resolve_base_url(base_url)
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = dict(default_headers or {})

    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"


class Tupana:
    """Cliente síncrono de la API v2 de Tupana.

    .. code-block:: python

        from tupana import Tupana

        tupana = Tupana()  # lee TUPANA_API_KEY
        batch = tupana.documents.create_batch(documents=[...], use_defaults=True)
    """

    documents: Documents
    payment_requests: PaymentRequests
    cessions: Cessions
    webhooks: Webhooks
    connections: Connections
    master_entities: MasterEntities

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._config = _Config(api_key, base_url, timeout, max_retries, default_headers)
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)
        self.documents = Documents(self)
        self.payment_requests = PaymentRequests(self)
        self.cessions = Cessions(self)
        self.webhooks = Webhooks(self)
        self.connections = Connections(self)
        self.master_entities = MasterEntities(self)

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Query] = None,
        body: Any = None,
        idempotency_key: Optional[str] = None,
        use_defaults: Optional[bool] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        """Llama cualquier endpoint v2 con auth, reintentos y errores tipados.

        Útil para endpoints sin método propio (folios, libros, sincronización…)::

            tupana.request("GET", "/folios/", query={"master_entity_id": "ment_…"})
        """
        method = method.upper()
        cfg = self._config
        retries = cfg.max_retries if max_retries is None else max_retries
        req_headers = build_headers(
            cfg.api_key,
            cfg.default_headers,
            has_body=body is not None,
            idempotency_key=idempotency_key,
            use_defaults=use_defaults,
            extra=headers,
        )
        attempt = 0
        while True:
            try:
                response = self._http.request(
                    method,
                    cfg.url(path),
                    params=clean_query(query),
                    json=body,
                    headers=req_headers,
                    timeout=cfg.timeout if timeout is None else timeout,
                )
            except httpx.TimeoutException as exc:
                if attempt < retries and can_retry(method, idempotency_key, None):
                    time.sleep(retry_delay(attempt))
                    attempt += 1
                    continue
                raise APITimeoutError() from exc
            except httpx.TransportError as exc:
                if attempt < retries and can_retry(method, idempotency_key, None):
                    time.sleep(retry_delay(attempt))
                    attempt += 1
                    continue
                raise APIConnectionError(f"No se pudo conectar con Tupana: {exc}") from exc

            if response.is_success:
                return parse_response(response)
            if attempt < retries and can_retry(method, idempotency_key, response.status_code):
                time.sleep(retry_delay(attempt, response.headers))
                attempt += 1
                continue
            raise make_api_error(response)

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Tupana:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()


class AsyncTupana:
    """Cliente asíncrono de la API v2 de Tupana.

    .. code-block:: python

        from tupana import AsyncTupana

        async with AsyncTupana() as tupana:
            batch = await tupana.documents.create_batch(documents=[...], use_defaults=True)
    """

    documents: AsyncDocuments
    payment_requests: AsyncPaymentRequests
    cessions: AsyncCessions
    webhooks: AsyncWebhooks
    connections: AsyncConnections
    master_entities: AsyncMasterEntities

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._config = _Config(api_key, base_url, timeout, max_retries, default_headers)
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self.documents = AsyncDocuments(self)
        self.payment_requests = AsyncPaymentRequests(self)
        self.cessions = AsyncCessions(self)
        self.webhooks = AsyncWebhooks(self)
        self.connections = AsyncConnections(self)
        self.master_entities = AsyncMasterEntities(self)

    @property
    def base_url(self) -> str:
        return self._config.base_url

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Query] = None,
        body: Any = None,
        idempotency_key: Optional[str] = None,
        use_defaults: Optional[bool] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        """Versión asíncrona de :meth:`Tupana.request`."""
        method = method.upper()
        cfg = self._config
        retries = cfg.max_retries if max_retries is None else max_retries
        req_headers = build_headers(
            cfg.api_key,
            cfg.default_headers,
            has_body=body is not None,
            idempotency_key=idempotency_key,
            use_defaults=use_defaults,
            extra=headers,
        )
        attempt = 0
        while True:
            try:
                response = await self._http.request(
                    method,
                    cfg.url(path),
                    params=clean_query(query),
                    json=body,
                    headers=req_headers,
                    timeout=cfg.timeout if timeout is None else timeout,
                )
            except httpx.TimeoutException as exc:
                if attempt < retries and can_retry(method, idempotency_key, None):
                    await asyncio.sleep(retry_delay(attempt))
                    attempt += 1
                    continue
                raise APITimeoutError() from exc
            except httpx.TransportError as exc:
                if attempt < retries and can_retry(method, idempotency_key, None):
                    await asyncio.sleep(retry_delay(attempt))
                    attempt += 1
                    continue
                raise APIConnectionError(f"No se pudo conectar con Tupana: {exc}") from exc

            if response.is_success:
                return parse_response(response)
            if attempt < retries and can_retry(method, idempotency_key, response.status_code):
                await asyncio.sleep(retry_delay(attempt, response.headers))
                attempt += 1
                continue
            raise make_api_error(response)

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncTupana:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.close()


AnyClient = Union[Tupana, AsyncTupana]
