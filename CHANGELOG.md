# Changelog

## 0.1.1 (2026-10-20)

- `documents.create_batch` acepta hasta 500 documentos por llamada, el límite real de la API.

## 0.1.0 (2026-10-20)

Primera versión pública.

- Clientes `Tupana` (síncrono) y `AsyncTupana` (asíncrono) para la API v2 (`https://api.tupana.ai/v2`), basados en httpx.
- Recursos: `documents` (emisión en lote, estado del lote, `wait_for_batch`, listado con auto-paginación, detalle, estados), `payment_requests`, `cessions`, `webhooks`, `connections`, `master_entities` y `request` para el resto de los endpoints.
- Reintentos con backoff exponencial y `Retry-After`; `Idempotency-Key` automático en `documents.create_batch`.
- Errores tipados con el envelope v2 (`type`, `code`, `param`, `request_id`, `doc_url`).
- Verificación de webhooks (`X-Pana-Signature`, HMAC SHA-256).
- Tipos `TypedDict` derivados del OpenAPI v2 (`tupana.types`).
