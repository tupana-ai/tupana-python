"""Tipos (``TypedDict``) de la API v2 de Tupana.

Se derivan del OpenAPI v2 (https://docs.tupana.ai/api-reference/openapi-v2.json)
y de lo que el backend devuelve hoy. Son diccionarios comunes en runtime: puedes
pasar ``dict`` literales y el type checker te avisará de campos mal escritos.
Las respuestas son ``total=False`` para que un campo nuevo de la API nunca rompa
tu código.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from typing_extensions import Literal, NotRequired, TypedDict

__all__ = [
    "Batch",
    "BatchCreateResponse",
    "BatchDocumentResult",
    "BatchDocumentSummary",
    "BatchWarning",
    "Cession",
    "CessionBatch",
    "CessionBatchCreateParams",
    "CessionBatchCreateResponse",
    "Connection",
    "ConnectionList",
    "DetailItem",
    "Document",
    "DocumentHeader",
    "DocumentInput",
    "DocumentIssuer",
    "DocumentReceiver",
    "DteRecipient",
    "DteType",
    "ListMeta",
    "ListResponse",
    "MasterEntity",
    "PaymentRequest",
    "PaymentRequestCreateParams",
    "PaymentRequestItem",
    "ReferenceItem",
    "WebhookCreateParams",
    "WebhookEndpoint",
    "WebhookEvent",
    "WebhookEventType",
    "WebhookUpdateParams",
]

# ── Envelope de listas v2 ────────────────────────────────────────────────────


class ListMeta(TypedDict, total=False):
    page: Optional[int]
    page_size: Optional[int]
    total: int
    total_pages: Optional[int]


class ListLinks(TypedDict, total=False):
    next: Optional[str]
    prev: Optional[str]


class ListResponse(TypedDict, total=False):
    """Toda lista v2 responde ``{"data": [...], "meta": {...}, "links": {...}}``."""

    data: List[Dict[str, Any]]
    meta: ListMeta
    links: ListLinks


# ── Documentos ───────────────────────────────────────────────────────────────

DteTypeCode = Literal[
    "33", "34", "39", "41", "46", "52", "56", "61", "80", "90", "110", "111", "112"
]


class DteType(TypedDict):
    code: Union[DteTypeCode, str]


class DocumentIssuer(TypedDict):
    """Emisor. Con ``use_defaults=True`` basta el ``rut``."""

    rut: str
    business_name: NotRequired[str]
    phone_number: NotRequired[str]
    email: NotRequired[str]
    business_activity: NotRequired[str]
    activity_code: NotRequired[int]
    sii_branch_code: NotRequired[str]
    address: NotRequired[str]
    district: NotRequired[str]
    city: NotRequired[str]


class DocumentReceiver(TypedDict):
    """Receptor. Con ``use_defaults=True`` basta el ``rut``."""

    rut: str
    business_name: NotRequired[str]
    contact: NotRequired[str]
    business_activity: NotRequired[str]
    address: NotRequired[str]
    district: NotRequired[str]
    city: NotRequired[str]


class DetailItem(TypedDict):
    item_name: str
    quantity: float
    #: Precio unitario neto (sin IVA). En boletas puedes usar ``gross_unit_price``.
    unit_price: NotRequired[float]
    gross_unit_price: NotRequired[float]
    is_exempt: NotRequired[bool]
    item_description: NotRequired[str]
    discount_percent: NotRequired[float]
    item_code: NotRequired[str]
    unit: NotRequired[str]
    other_tax: NotRequired[float]
    item_type_code: NotRequired[int]
    line_number: NotRequired[int]


class ReferenceItem(TypedDict):
    reference_folio: int
    reference_date: str
    dte_type_code: str
    reference_reason: NotRequired[str]


class DocumentHeader(TypedDict, total=False):
    purchase_transaction_type: Optional[str]
    sale_transaction_type: Optional[str]
    #: "1" contado, "2" crédito, "3" sin costo.
    payment_method: Optional[Literal["1", "2", "3"]]
    due_date: Optional[str]
    vat_withheld: Optional[bool]
    retention_type: Optional[Literal["RETRECEPTOR", "RETCONTRIBUYENTE"]]
    purchase_type: Optional[str]


class DocumentInput(TypedDict):
    """Un documento a emitir (``POST /documents/batch/``)."""

    dte_type: DteType
    document_issuer: DocumentIssuer
    document_receiver: DocumentReceiver
    details: List[DetailItem]
    date_issued: NotRequired[str]
    folio: NotRequired[str]
    header: NotRequired[DocumentHeader]
    references: NotRequired[List[ReferenceItem]]
    export_data: NotRequired[Dict[str, Any]]
    transport_data: NotRequired[Dict[str, Any]]
    #: Campos propios (ej. ``{"external_order_id": "PED-123"}``), buscables con ``json_param``.
    json_param: NotRequired[Optional[Dict[str, Any]]]
    additional_info: NotRequired[Optional[str]]


BatchStatus = Literal["created", "processing", "completed", "failed"]
BatchDocumentStatus = Literal[
    "created",
    "processing",
    "success",
    "invalid",
    "temporary_error",
    "permanent_error",
    "incomplete",
]


class BatchDocumentSummary(TypedDict, total=False):
    id: str
    folio: Optional[str]
    date_issued: str
    amount_with_iva: float
    receiver_id: Optional[str]
    is_draft: bool
    can_be_issued: bool
    dte_type: Dict[str, Any]
    sender: Optional[Dict[str, Any]]
    receiver: Optional[Dict[str, Any]]
    items: List[Dict[str, Any]]
    document_total: Optional[Dict[str, Any]]
    #: URL presignada al PDF (válida por 2 horas).
    pdf_url: Optional[str]
    pdf_download_url: Optional[str]


class BatchDocumentResult(TypedDict, total=False):
    index: int
    status: Union[BatchDocumentStatus, str]
    #: Emitido, pero el SII todavía no entrega su veredicto (el PDF ya está).
    confirmation_pending: bool
    document: Optional[BatchDocumentSummary]


class BatchWarning(TypedDict, total=False):
    document_index: int
    field: str
    code: str
    message: str
    suggestion: Optional[str]


class BatchCreateResponse(TypedDict, total=False):
    batch_id: str
    status: Union[BatchStatus, str]
    created_at: str
    documents: List[BatchDocumentResult]
    warnings: List[BatchWarning]


class Batch(TypedDict, total=False):
    id: str
    status: Union[BatchStatus, str]
    idempotency_key: Optional[str]
    created_at: str
    updated_at: str
    documents: List[BatchDocumentResult]


class Document(TypedDict, total=False):
    id: str
    folio: Optional[str]
    date_issued: str
    dte_type_code: str
    dte_type_description: str
    amount_with_iva: float
    amount_without_iva: Optional[float]
    amount_iva: Optional[float]
    currency: str
    sender_id: str
    sender_name: str
    sender_tax_id: str
    receiver_id: Optional[str]
    receiver_name: Optional[str]
    receiver_tax_id: Optional[str]
    is_paid: bool
    has_credit_note: bool
    has_trace: bool
    state: Optional[str]
    pdf: Optional[str]
    xml: Optional[str]
    details: Optional[List[Dict[str, Any]]]
    references: List[Dict[str, Any]]
    traces: List[Dict[str, Any]]
    json_param: Optional[Dict[str, Any]]
    additional_info: Optional[str]
    created_at: str
    updated_at: str


# ── Cobros ───────────────────────────────────────────────────────────────────


class DteRecipient(TypedDict):
    rut: str
    name: str
    email: NotRequired[str]


class PaymentRequestItem(TypedDict):
    description: str
    quantity: float
    unit_price: int


class PaymentRequestCreateParams(TypedDict):
    """Sesión de cobro.

    - Modo emisión: ``amount``, ``target_dte_type``, ``dte_recipient`` e ``items``.
    - Modo cobro directo: ``document_ids`` de documentos ya emitidos.
    """

    recipient_id: Union[str, int]
    amount: NotRequired[int]
    currency: NotRequired[Literal["CLP"]]
    redirect_url: NotRequired[str]
    target_dte_type: NotRequired[Literal[33, 39, 41]]
    dte_recipient: NotRequired[DteRecipient]
    items: NotRequired[List[PaymentRequestItem]]
    document_ids: NotRequired[List[Union[str, int]]]
    expires_in_minutes: NotRequired[int]
    skip_portal: NotRequired[bool]
    auto_issue: NotRequired[bool]
    #: Idempotencia: repetir con el mismo ``external_id`` devuelve la sesión original.
    external_id: NotRequired[str]
    metadata: NotRequired[Dict[str, Any]]


class PaymentRequest(TypedDict, total=False):
    payment_request_id: Union[str, int]
    status: str
    payment_url: str
    expires_at: str
    created_at: str
    amount: float
    target_dte_type: Optional[Union[str, int]]
    auto_issue: Optional[bool]
    external_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    issued_document_id: Optional[Union[str, int]]
    document_ids: List[Union[str, int]]


# ── Cesiones ─────────────────────────────────────────────────────────────────


class CessionBatchCreateParams(TypedDict):
    master_entity_id: Union[str, int]
    document_ids: List[Union[str, int]]
    #: RUT del cesionario sin puntos, sin guion y sin DV (ej. ``"76798398"``).
    assignee_rut: str
    assignee_dv: str
    assignee_business_name: str
    assignee_address: str
    assignee_email: str
    assignor_email: NotRequired[str]


class CessionBatchCreateResponse(TypedDict, total=False):
    success: bool
    status: str
    total: int
    message: str
    ws_channel: str
    cession_batch_id: str


class CessionBatch(TypedDict, total=False):
    id: str
    status: str
    total: int
    success_count: int
    failed_count: int
    assignee_business_name: str
    assignee_rut: str
    created_at: str
    error_message: Optional[str]
    batch_cessions: List[Dict[str, Any]]


class Cession(TypedDict, total=False):
    id: str
    document_id: str
    document_folio: str
    document_amount: float
    assignee_rut: str
    assignee_business_name: str
    assignment_amount: float
    status: str
    status_message: Optional[str]
    source: str
    aec_url: Optional[str]
    created_at: str


# ── Webhooks ─────────────────────────────────────────────────────────────────

WebhookEventType = Literal[
    "document.issued",
    "document.issue_failed",
    "document.updated",
    "document.delivered",
    "document.rejected",
    "document.trace_updated",
    "document.paid",
    "document.unpaid",
    "document.cancelled",
    "scheduled_document.created",
    "scheduled_document.updated",
    "scheduled_document.run_started",
    "scheduled_document.run_succeeded",
    "scheduled_document.run_failed",
    "payment_request.paid",
    "payment_request.document_issued",
    "payment_request.expired",
    "credential.invalid",
    "credential.validated",
    "connection.active",
    "connection.requires_action",
    "folio_request.completed",
    "folio_request.failed",
    "folio_request.authorized_without_caf",
    "batch.intake_failed",
    "payroll_run.closed",
    "payroll_run.reopened",
    "payroll_termination.confirmed",
    "payslip.signed",
    "webhook.test",
]


class WebhookCreateParams(TypedDict):
    master_entity_id: str
    url: str
    events: List[Union[WebhookEventType, str]]
    #: Configúralo siempre: sin ``secret`` las entregas no vienen firmadas.
    secret: NotRequired[str]
    is_active: NotRequired[bool]
    environment: NotRequired[Literal["both", "production", "sandbox"]]
    api_version: NotRequired[Literal[1, 2]]


class WebhookUpdateParams(TypedDict, total=False):
    url: str
    events: List[Union[WebhookEventType, str]]
    secret: str
    is_active: bool
    environment: Literal["both", "production", "sandbox"]
    api_version: Literal[1, 2]


class WebhookEndpoint(TypedDict, total=False):
    id: str
    url: str
    events: List[str]
    secret: Optional[str]
    is_active: bool
    environment: str
    api_version: int
    success_rate: float
    last_status_code: Optional[int]
    last_sent_at: Optional[str]
    created_at: str
    updated_at: str


class WebhookEvent(TypedDict, total=False):
    """Notificación que Tupana envía a tu URL."""

    event: Union[WebhookEventType, str]
    created_at: str
    data: Dict[str, Any]


# ── Conexiones y entidades ───────────────────────────────────────────────────


class Connection(TypedDict, total=False):
    connection_id: str
    company_id: str
    provider: str
    type: str
    name: str
    tax_id: str
    environment: str
    status: str
    last_verified_at: str
    business_activity: str
    activity_code: Optional[int]
    address: str
    district: str
    city: str


class ConnectionList(TypedDict, total=False):
    data: List[Connection]
    total: int
    limit: int


class MasterEntity(TypedDict, total=False):
    id: str
    tax_id: str
    name: str
    email: Optional[str]
    addresses: List[Dict[str, Any]]
    activities: List[Dict[str, Any]]
