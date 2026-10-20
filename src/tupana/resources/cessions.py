"""Cesiones de facturas (AEC)."""

from __future__ import annotations

from typing import Literal, Optional, cast

from .._base import path_id
from ..types import (
    Cession,
    CessionBatch,
    CessionBatchCreateParams,
    CessionBatchCreateResponse,
    ListResponse,
)
from ._shared import AsyncResource, SyncResource, compact

__all__ = ["AsyncCessions", "Cessions"]

DocumentType = Literal["issued", "received"]


class Cessions(SyncResource):
    def create_batch(self, params: CessionBatchCreateParams) -> CessionBatchCreateResponse:
        """Cede varias facturas (``POST /cessions/batch/``). El 202 solo confirma que se aceptó."""
        return cast(
            CessionBatchCreateResponse,
            self._client.request("POST", "/cessions/batch/", body=dict(params)),
        )

    def retrieve_batch(self, cession_batch_id: str) -> CessionBatch:
        """Resultado del lote, con el error real del SII por documento."""
        return cast(
            CessionBatch,
            self._client.request("GET", f"/cessions/batch/{path_id(cession_batch_id)}/"),
        )

    def list(
        self,
        master_entity_id: str,
        *,
        document_type: Optional[DocumentType] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> ListResponse:
        query = compact(
            {
                "master_entity_id": master_entity_id,
                "document_type": document_type,
                "date_from": date_from,
                "date_to": date_to,
                "status": status,
                "search": search,
                "page": page,
                "page_size": page_size,
            }
        )
        return cast(ListResponse, self._client.request("GET", "/cessions/", query=query))

    def retrieve(self, cession_id: str) -> Cession:
        return cast(Cession, self._client.request("GET", f"/cessions/{path_id(cession_id)}/"))


class AsyncCessions(AsyncResource):
    async def create_batch(self, params: CessionBatchCreateParams) -> CessionBatchCreateResponse:
        return cast(
            CessionBatchCreateResponse,
            await self._client.request("POST", "/cessions/batch/", body=dict(params)),
        )

    async def retrieve_batch(self, cession_batch_id: str) -> CessionBatch:
        return cast(
            CessionBatch,
            await self._client.request("GET", f"/cessions/batch/{path_id(cession_batch_id)}/"),
        )

    async def list(
        self,
        master_entity_id: str,
        *,
        document_type: Optional[DocumentType] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> ListResponse:
        query = compact(
            {
                "master_entity_id": master_entity_id,
                "document_type": document_type,
                "date_from": date_from,
                "date_to": date_to,
                "status": status,
                "search": search,
                "page": page,
                "page_size": page_size,
            }
        )
        return cast(ListResponse, await self._client.request("GET", "/cessions/", query=query))

    async def retrieve(self, cession_id: str) -> Cession:
        return cast(Cession, await self._client.request("GET", f"/cessions/{path_id(cession_id)}/"))
