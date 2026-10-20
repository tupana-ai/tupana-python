"""Empresas conectadas y búsqueda de contribuyentes por RUT."""

from __future__ import annotations

from typing import Any, Optional, cast

from .._base import path_id
from ..types import ConnectionList, MasterEntity
from ._shared import AsyncResource, SyncResource

__all__ = ["AsyncConnections", "AsyncMasterEntities", "Connections", "MasterEntities"]


class Connections(SyncResource):
    def list(self, *, search: Optional[str] = None, limit: Optional[int] = None) -> ConnectionList:
        """Empresas conectadas a tu integración (``GET /connections/``)."""
        return cast(
            ConnectionList,
            self._client.request("GET", "/connections/", query={"search": search, "limit": limit}),
        )

    def deactivate(self, connection_id: str) -> Any:
        """Desactiva una conexión (``DELETE /connections/{connection_id}/``)."""
        return self._client.request("DELETE", f"/connections/{path_id(connection_id)}/")


class AsyncConnections(AsyncResource):
    async def list(
        self, *, search: Optional[str] = None, limit: Optional[int] = None
    ) -> ConnectionList:
        return cast(
            ConnectionList,
            await self._client.request(
                "GET", "/connections/", query={"search": search, "limit": limit}
            ),
        )

    async def deactivate(self, connection_id: str) -> Any:
        return await self._client.request("DELETE", f"/connections/{path_id(connection_id)}/")


class MasterEntities(SyncResource):
    def lookup(self, rut: str) -> MasterEntity:
        """Razón social, direcciones y actividades de un RUT (``GET /master-entities/?rut=``)."""
        return cast(
            MasterEntity, self._client.request("GET", "/master-entities/", query={"rut": rut})
        )


class AsyncMasterEntities(AsyncResource):
    async def lookup(self, rut: str) -> MasterEntity:
        return cast(
            MasterEntity, await self._client.request("GET", "/master-entities/", query={"rut": rut})
        )
