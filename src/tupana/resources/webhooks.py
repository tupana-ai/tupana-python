"""Configuración de webhooks y verificación de las notificaciones entrantes."""

from __future__ import annotations

from typing import Any, Mapping, Optional, cast

from .._base import path_id
from ..types import (
    ListResponse,
    WebhookCreateParams,
    WebhookEndpoint,
    WebhookEvent,
    WebhookUpdateParams,
)
from ..webhooks import (
    Payload,
    compute_webhook_signature,
    construct_webhook_event,
    verify_webhook_signature,
)
from ._shared import AsyncResource, SyncResource

__all__ = ["AsyncWebhooks", "Webhooks"]


class _SignatureHelpers:
    @staticmethod
    def unwrap(payload: Payload, headers: Mapping[str, Any], secret: str) -> WebhookEvent:
        """Verifica ``X-Pana-Signature`` y devuelve el evento. ``payload`` = cuerpo crudo."""
        return construct_webhook_event(payload, headers, secret)

    @staticmethod
    def verify_signature(payload: Payload, signature: Optional[str], secret: str) -> bool:
        return verify_webhook_signature(payload, signature, secret)

    @staticmethod
    def sign(payload: Payload, secret: str) -> str:
        """Firma un payload como lo hace Tupana (útil para testear tu receptor)."""
        return compute_webhook_signature(payload, secret)


class Webhooks(SyncResource, _SignatureHelpers):
    def create(self, params: WebhookCreateParams) -> WebhookEndpoint:
        """Crea un webhook. Configura siempre un ``secret`` para poder verificar la firma."""
        return cast(WebhookEndpoint, self._client.request("POST", "/webhooks/", body=dict(params)))

    def list(self, *, master_entity_id: Optional[str] = None) -> ListResponse:
        return cast(
            ListResponse,
            self._client.request("GET", "/webhooks/", query={"master_entity_id": master_entity_id}),
        )

    def retrieve(self, webhook_id: str) -> WebhookEndpoint:
        return cast(
            WebhookEndpoint, self._client.request("GET", f"/webhooks/{path_id(webhook_id)}/")
        )

    def update(self, webhook_id: str, params: WebhookUpdateParams) -> WebhookEndpoint:
        return cast(
            WebhookEndpoint,
            self._client.request("PATCH", f"/webhooks/{path_id(webhook_id)}/", body=dict(params)),
        )

    def delete(self, webhook_id: str) -> None:
        self._client.request("DELETE", f"/webhooks/{path_id(webhook_id)}/")


class AsyncWebhooks(AsyncResource, _SignatureHelpers):
    async def create(self, params: WebhookCreateParams) -> WebhookEndpoint:
        return cast(
            WebhookEndpoint, await self._client.request("POST", "/webhooks/", body=dict(params))
        )

    async def list(self, *, master_entity_id: Optional[str] = None) -> ListResponse:
        return cast(
            ListResponse,
            await self._client.request(
                "GET", "/webhooks/", query={"master_entity_id": master_entity_id}
            ),
        )

    async def retrieve(self, webhook_id: str) -> WebhookEndpoint:
        return cast(
            WebhookEndpoint, await self._client.request("GET", f"/webhooks/{path_id(webhook_id)}/")
        )

    async def update(self, webhook_id: str, params: WebhookUpdateParams) -> WebhookEndpoint:
        return cast(
            WebhookEndpoint,
            await self._client.request(
                "PATCH", f"/webhooks/{path_id(webhook_id)}/", body=dict(params)
            ),
        )

    async def delete(self, webhook_id: str) -> None:
        await self._client.request("DELETE", f"/webhooks/{path_id(webhook_id)}/")
