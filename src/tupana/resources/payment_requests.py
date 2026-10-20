"""Cobros: links de pago que emiten el DTE al pagarse o saldan documentos existentes."""

from __future__ import annotations

from typing import Optional, Union, cast

from .._base import path_id
from ..types import ListResponse, PaymentRequest, PaymentRequestCreateParams
from ._shared import AsyncResource, SyncResource

__all__ = ["AsyncPaymentRequests", "PaymentRequests"]


class PaymentRequests(SyncResource):
    def create(self, params: PaymentRequestCreateParams) -> PaymentRequest:
        """Crea una sesión de cobro (``POST /payment-requests/``) y devuelve el ``payment_url``.

        Usa ``external_id`` como llave de idempotencia: si ya existe una sesión con
        ese ``external_id`` para tu API key, la API devuelve la original.
        """
        return cast(
            PaymentRequest, self._client.request("POST", "/payment-requests/", body=dict(params))
        )

    def list(self, *, status: Optional[str] = None) -> ListResponse:
        """Tus cobros, opcionalmente filtrados por estado."""
        return cast(
            ListResponse,
            self._client.request("GET", "/payment-requests/", query={"status": status}),
        )

    def retrieve(self, payment_request_id: Union[str, int]) -> PaymentRequest:
        return cast(
            PaymentRequest,
            self._client.request("GET", f"/payment-requests/{path_id(payment_request_id)}/"),
        )

    def issue(self, payment_request_id: Union[str, int]) -> PaymentRequest:
        """Emite el DTE de un cobro pagado creado con ``auto_issue=False``."""
        return cast(
            PaymentRequest,
            self._client.request(
                "PATCH",
                f"/payment-requests/{path_id(payment_request_id)}/",
                body={"status": "issued"},
            ),
        )


class AsyncPaymentRequests(AsyncResource):
    async def create(self, params: PaymentRequestCreateParams) -> PaymentRequest:
        return cast(
            PaymentRequest,
            await self._client.request("POST", "/payment-requests/", body=dict(params)),
        )

    async def list(self, *, status: Optional[str] = None) -> ListResponse:
        return cast(
            ListResponse,
            await self._client.request("GET", "/payment-requests/", query={"status": status}),
        )

    async def retrieve(self, payment_request_id: Union[str, int]) -> PaymentRequest:
        return cast(
            PaymentRequest,
            await self._client.request("GET", f"/payment-requests/{path_id(payment_request_id)}/"),
        )

    async def issue(self, payment_request_id: Union[str, int]) -> PaymentRequest:
        return cast(
            PaymentRequest,
            await self._client.request(
                "PATCH",
                f"/payment-requests/{path_id(payment_request_id)}/",
                body={"status": "issued"},
            ),
        )
