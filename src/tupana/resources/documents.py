"""Documentos tributarios electrónicos (DTE)."""

from __future__ import annotations

import asyncio
import time
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Union,
    cast,
)

from .._base import path_id, random_idempotency_key
from .._errors import BatchTimeoutError, TupanaError
from ..types import Batch, BatchCreateResponse, Document, DocumentInput, ListResponse
from ._shared import AsyncResource, SyncResource, compact, has_next_page

__all__ = ["MAX_BATCH_SIZE", "AsyncDocuments", "Documents"]

#: Máximo de documentos por llamada a ``create_batch``.
MAX_BATCH_SIZE = 500
FINAL_BATCH_STATUSES = frozenset({"completed", "failed"})


def _batch_body(
    documents: Sequence[DocumentInput], state: Optional[str], preview: Optional[bool]
) -> Dict[str, Any]:
    docs = list(documents)
    if not docs:
        raise TupanaError("`documents` debe traer al menos un documento")
    if len(docs) > MAX_BATCH_SIZE:
        raise TupanaError(
            f"Máximo {MAX_BATCH_SIZE} documentos por lote (recibí {len(docs)}). "
            "Divide el envío en varios lotes."
        )
    return compact({"documents": docs, "state": state, "preview": preview})


def _list_query(
    master_entity_id: str,
    json_param: Optional[Mapping[str, Union[str, int]]],
    filters: Mapping[str, Any],
) -> Dict[str, Any]:
    query: Dict[str, Any] = {"master_entity_id": master_entity_id, **compact(filters)}
    for key, value in (json_param or {}).items():
        query[f"json_param__{key}"] = value
    return query


class Documents(SyncResource):
    def create_batch(
        self,
        documents: Sequence[DocumentInput],
        *,
        state: Optional[Literal["issued", "draft"]] = None,
        preview: Optional[bool] = None,
        use_defaults: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> BatchCreateResponse:
        """Emite hasta 500 DTEs en una llamada (``POST /documents/batch/``).

        La emisión al SII es asíncrona: usa :meth:`retrieve_batch`,
        :meth:`wait_for_batch` o el webhook ``document.issued``.

        Si no pasas ``idempotency_key``, el SDK genera una para que los reintentos
        automáticos nunca emitan dos veces. Usa una tuya y estable (ej. el id de
        tu pedido) para que también sea seguro reintentar desde otro proceso.

        :param state: ``"issued"`` (por defecto) emite; ``"draft"`` crea borradores.
        :param preview: con ``state="draft"``, devuelve además el PDF del borrador.
        :param use_defaults: header ``X-Use-Defaults``: la API completa emisor,
            receptor, fecha y forma de pago.
        """
        return cast(
            BatchCreateResponse,
            self._client.request(
                "POST",
                "/documents/batch/",
                body=_batch_body(documents, state, preview),
                use_defaults=use_defaults,
                idempotency_key=idempotency_key or random_idempotency_key(),
                timeout=timeout,
            ),
        )

    def retrieve_batch(self, batch_id: str) -> Batch:
        """Estado del lote y de cada documento (``GET /documents/batch/{id}/``)."""
        return cast(Batch, self._client.request("GET", f"/documents/batch/{path_id(batch_id)}/"))

    def wait_for_batch(
        self,
        batch_id: str,
        *,
        interval: float = 2.0,
        timeout: float = 120.0,
        on_poll: Optional[Callable[[Batch], None]] = None,
    ) -> Batch:
        """Consulta el lote hasta ``completed`` o ``failed``.

        Pensado para scripts; en producción usa webhooks.
        """
        deadline = time.monotonic() + timeout
        while True:
            batch = self.retrieve_batch(batch_id)
            if str(batch.get("status")) in FINAL_BATCH_STATUSES:
                return batch
            if on_poll:
                on_poll(batch)
            if time.monotonic() + interval > deadline:
                raise BatchTimeoutError(batch_id, batch)
            time.sleep(interval)

    def list(
        self,
        master_entity_id: str,
        *,
        document_type: Optional[Literal["issued", "received"]] = None,
        folio: Optional[Union[int, str]] = None,
        search: Optional[str] = None,
        dte_type__code__in: Optional[List[str]] = None,
        issuer_tax_id: Optional[str] = None,
        issue_date_gte: Optional[str] = None,
        issue_date_lte: Optional[str] = None,
        reception_date_from: Optional[str] = None,
        reception_date_to: Optional[str] = None,
        include_trace_events: Optional[bool] = None,
        json_param: Optional[Mapping[str, Union[str, int]]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        fields: Optional[str] = None,
    ) -> ListResponse:
        """Documentos emitidos o recibidos por una empresa (``GET /documents/``)."""
        filters = dict(locals())
        for key in ("self", "master_entity_id", "json_param"):
            filters.pop(key, None)
        return cast(
            ListResponse,
            self._client.request(
                "GET", "/documents/", query=_list_query(master_entity_id, json_param, filters)
            ),
        )

    def list_auto_paging(self, master_entity_id: str, **params: Any) -> Iterator[Document]:
        """Itera los documentos de todas las páginas."""
        page = int(params.pop("page", None) or 1)
        while True:
            result = self.list(master_entity_id, page=page, **params)
            for item in result.get("data") or []:
                yield cast(Document, item)
            if not has_next_page(result, page):
                return
            page += 1

    def retrieve(self, document_id: str) -> Document:
        """Detalle con PDF, XML y trazas del SII (``GET /documents/{id}/``)."""
        return cast(Document, self._client.request("GET", f"/documents/{path_id(document_id)}/"))

    def list_states(self, document_id: str) -> Any:
        """Historial de estados del documento."""
        return self._client.request("GET", f"/documents/{path_id(document_id)}/states/")

    def create_state(self, document_id: str, body: Mapping[str, Any]) -> Any:
        """Registra un estado, ej. ``{"event_code": "ANNULLED"}`` para anular una guía."""
        return self._client.request(
            "POST", f"/documents/{path_id(document_id)}/states/", body=dict(body)
        )


class AsyncDocuments(AsyncResource):
    async def create_batch(
        self,
        documents: Sequence[DocumentInput],
        *,
        state: Optional[Literal["issued", "draft"]] = None,
        preview: Optional[bool] = None,
        use_defaults: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> BatchCreateResponse:
        """Versión asíncrona de :meth:`Documents.create_batch`."""
        return cast(
            BatchCreateResponse,
            await self._client.request(
                "POST",
                "/documents/batch/",
                body=_batch_body(documents, state, preview),
                use_defaults=use_defaults,
                idempotency_key=idempotency_key or random_idempotency_key(),
                timeout=timeout,
            ),
        )

    async def retrieve_batch(self, batch_id: str) -> Batch:
        return cast(
            Batch, await self._client.request("GET", f"/documents/batch/{path_id(batch_id)}/")
        )

    async def wait_for_batch(
        self,
        batch_id: str,
        *,
        interval: float = 2.0,
        timeout: float = 120.0,
        on_poll: Optional[Callable[[Batch], None]] = None,
    ) -> Batch:
        deadline = time.monotonic() + timeout
        while True:
            batch = await self.retrieve_batch(batch_id)
            if str(batch.get("status")) in FINAL_BATCH_STATUSES:
                return batch
            if on_poll:
                on_poll(batch)
            if time.monotonic() + interval > deadline:
                raise BatchTimeoutError(batch_id, batch)
            await asyncio.sleep(interval)

    async def list(
        self,
        master_entity_id: str,
        *,
        document_type: Optional[Literal["issued", "received"]] = None,
        folio: Optional[Union[int, str]] = None,
        search: Optional[str] = None,
        dte_type__code__in: Optional[List[str]] = None,
        issuer_tax_id: Optional[str] = None,
        issue_date_gte: Optional[str] = None,
        issue_date_lte: Optional[str] = None,
        reception_date_from: Optional[str] = None,
        reception_date_to: Optional[str] = None,
        include_trace_events: Optional[bool] = None,
        json_param: Optional[Mapping[str, Union[str, int]]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        fields: Optional[str] = None,
    ) -> ListResponse:
        filters = dict(locals())
        for key in ("self", "master_entity_id", "json_param"):
            filters.pop(key, None)
        return cast(
            ListResponse,
            await self._client.request(
                "GET", "/documents/", query=_list_query(master_entity_id, json_param, filters)
            ),
        )

    async def list_auto_paging(
        self, master_entity_id: str, **params: Any
    ) -> AsyncIterator[Document]:
        page = int(params.pop("page", None) or 1)
        while True:
            result = await self.list(master_entity_id, page=page, **params)
            for item in result.get("data") or []:
                yield cast(Document, item)
            if not has_next_page(result, page):
                return
            page += 1

    async def retrieve(self, document_id: str) -> Document:
        return cast(
            Document, await self._client.request("GET", f"/documents/{path_id(document_id)}/")
        )

    async def list_states(self, document_id: str) -> Any:
        return await self._client.request("GET", f"/documents/{path_id(document_id)}/states/")

    async def create_state(self, document_id: str, body: Mapping[str, Any]) -> Any:
        return await self._client.request(
            "POST", f"/documents/{path_id(document_id)}/states/", body=dict(body)
        )
