# Tupana para Python

[![CI](https://github.com/tupana-ai/tupana-python/actions/workflows/ci.yml/badge.svg)](https://github.com/tupana-ai/tupana-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tupana.svg)](https://pypi.org/project/tupana/)
[![Python](https://img.shields.io/pypi/pyversions/tupana.svg)](https://pypi.org/project/tupana/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

SDK oficial de la [API v2 de Tupana](https://docs.tupana.ai) para Python: facturación electrónica ante el SII, links de pago (recaudación), cesión de facturas y webhooks.

```bash
pip install tupana
```

- Cliente síncrono (`Tupana`) y asíncrono (`AsyncTupana`) sobre [httpx](https://www.python-httpx.org/).
- Tipado: `TypedDict` derivados del OpenAPI v2, `py.typed`, verificado con `mypy --strict`.
- Reintentos automáticos con backoff ante `429` y `5xx`, respetando `Retry-After`.
- Emisión idempotente: `documents.create_batch` envía un `Idempotency-Key` para que un reintento nunca emita dos veces.
- Errores tipados (`RateLimitError`, `UnprocessableEntityError`…) con `code`, `param` y `request_id`.
- Verificación de la firma de webhooks (`X-Pana-Signature`).
- Python 3.9 o superior.

## Instalación

```bash
pip install tupana
# o: uv add tupana · poetry add tupana
```

Paquete en PyPI: [pypi.org/project/tupana](https://pypi.org/project/tupana/).

## Antes de empezar

1. Crea tu cuenta y tu API key en [developers.tupana.ai](https://developers.tupana.ai) (en la plataforma: **Configuración → Integraciones API**). Tienes una key de **sandbox** y una de **producción**: el código es el mismo, solo cambia la key.
2. Conecta la empresa emisora con sus credenciales del SII (Tupana Connect). Sin una conexión activa la API responde `no_active_credentials`.
3. Guarda la key en una variable de entorno:

```bash
export TUPANA_API_KEY="tu-api-key"
```

## Inicio rápido: emitir una factura

```python
from tupana import Tupana

tupana = Tupana()  # lee TUPANA_API_KEY

batch = tupana.documents.create_batch(
    [
        {
            "dte_type": {"code": "33"},  # Factura electrónica
            "document_issuer": {"rut": "76543210-3"},  # tu empresa
            "document_receiver": {"rut": "77777777-7"},  # tu cliente
            "details": [
                {"item_name": "Asesoría contable octubre", "quantity": 1, "unit_price": 150000}
            ],
        }
    ],
    use_defaults=True,  # X-Use-Defaults: la API completa razón social, giro, dirección, fecha y forma de pago
)

print(batch["batch_id"])  # la emisión al SII sigue en segundo plano

# En un script puedes esperar el resultado. En producción, usa webhooks.
result = tupana.documents.wait_for_batch(batch["batch_id"])
for doc in result["documents"]:
    print(doc["index"], doc["status"], (doc.get("document") or {}).get("folio"))
```

`create_batch` acepta hasta **200 documentos** por llamada. Para cargas más grandes, divide en lotes (mira el ejemplo de [emisión masiva desde Excel o CSV](https://github.com/tupana-ai/tupana-examples)).

### Asíncrono

```python
import asyncio
from tupana import AsyncTupana


async def main() -> None:
    async with AsyncTupana() as tupana:
        batch = await tupana.documents.create_batch([invoice], use_defaults=True)
        async for doc in tupana.documents.list_auto_paging("ment_4829301923847"):
            print(doc["folio"])


asyncio.run(main())
```

### Borradores y vista previa

```python
draft = tupana.documents.create_batch([invoice], state="draft", preview=True)
```

Con `state="draft"` no se pide folio ni se envía nada al SII; `preview=True` devuelve el PDF del borrador.

### Idempotencia

Cada `create_batch` viaja con un header `Idempotency-Key`. Si no pasas uno, el SDK genera un UUID, así los reintentos automáticos del mismo proceso son seguros. Para que también sea seguro reintentar desde otro proceso, usa una key tuya y estable:

```python
tupana.documents.create_batch([invoice], idempotency_key=f"pedido-{order.id}")
```

Repetir la llamada con la misma key devuelve el lote original sin volver a emitir. Para reencontrar un documento aunque pierdas la respuesta, guarda tu propio id en `json_param` y búscalo después:

```python
page = tupana.documents.list("ment_4829301923847", json_param={"external_order_id": "PED-123"})
```

## Documentos

```python
page = tupana.documents.list(
    "ment_4829301923847",
    document_type="issued",  # o "received"
    dte_type__code__in=["33", "34"],
    issue_date_gte="2026-10-01",
    page_size=100,
)
print(page["meta"]["total"], len(page["data"]))

for doc in tupana.documents.list_auto_paging("ment_4829301923847"):
    print(doc["folio"], doc["amount_with_iva"])

doc = tupana.documents.retrieve("docu_9f2a7c1b8e4d0")  # con PDF, XML y trazas del SII
```

## Links de pago (recaudación)

```python
payment = tupana.payment_requests.create(
    {
        "recipient_id": "ment_4829301923847",  # quien recibe los fondos
        "amount": 50000,
        "target_dte_type": 39,  # boleta: se emite sola al confirmarse el pago
        "dte_recipient": {"rut": "11111111-1", "name": "Juan Soto", "email": "juan@ejemplo.com"},
        "items": [{"description": "Sesión de psicoterapia", "quantity": 1, "unit_price": 50000}],
        "external_id": "booking_abc123",  # idempotencia
        "redirect_url": "https://tuapp.cl/gracias",
    }
)
print(payment["payment_url"])  # redirige a tu cliente y espera el webhook payment_request.paid
```

## Cesiones

```python
res = tupana.cessions.create_batch(
    {
        "master_entity_id": "ment_4829301923847",
        "document_ids": ["docu_9f2a7c1b8e4d0"],
        "assignee_rut": "76798398",
        "assignee_dv": "0",
        "assignee_business_name": "Factoring SpA",
        "assignee_address": "Av. Apoquindo 1234, Las Condes",
        "assignee_email": "operaciones@factoring.cl",
    }
)
status = tupana.cessions.retrieve_batch(res["cession_batch_id"])
```

## Webhooks

Configura el webhook **con `secret`** y Tupana firmará cada entrega:

```python
tupana.webhooks.create(
    {
        "master_entity_id": "ment_4829301923847",
        "url": "https://tuapp.cl/webhooks/tupana",
        "events": ["document.issued", "document.rejected", "payment_request.paid"],
        "secret": os.environ["TUPANA_WEBHOOK_SECRET"],
    }
)
```

Cada notificación trae `X-Pana-Signature`: el HMAC SHA-256 (hex) del cuerpo crudo. Verifícalo **antes** de parsear el JSON. Con FastAPI:

```python
from fastapi import FastAPI, HTTPException, Request
from tupana import WebhookVerificationError, construct_webhook_event

app = FastAPI()


@app.post("/webhooks/tupana")
async def tupana_webhook(request: Request) -> dict:
    try:
        event = construct_webhook_event(
            await request.body(), request.headers, os.environ["TUPANA_WEBHOOK_SECRET"]
        )
    except WebhookVerificationError:
        raise HTTPException(status_code=400)
    # Deduplica por X-Pana-Event-Id: una entrega puede repetirse.
    if event["event"] == "document.issued":
        ...
    return {"ok": True}
```

La firma no incluye el timestamp, así que para descartar repeticiones guarda el `X-Pana-Event-Id` que ya procesaste.

## Errores

Todos los errores heredan de `TupanaError`; los de la API son `APIError` (o una subclase según el status):

```python
from tupana import APIError, UnprocessableEntityError

try:
    tupana.documents.create_batch(documents)
except UnprocessableEntityError as err:
    print(err.code, err.param, err.message)
except APIError as err:
    print(err.status_code, err.type, err.code, err.request_id, err.doc_url)
```

| Status | Clase |
| --- | --- |
| 400 | `BadRequestError` |
| 401 | `AuthenticationError` |
| 403 | `PermissionDeniedError` |
| 404 | `NotFoundError` |
| 409 | `ConflictError` |
| 413 | `PayloadTooLargeError` |
| 422 | `UnprocessableEntityError` |
| 429 | `RateLimitError` |
| 5xx | `InternalServerError` |
| red / timeout | `APIConnectionError` / `APITimeoutError` |

Cuando reportes un problema a soporte, incluye `err.request_id`. El catálogo de códigos está en [docs.tupana.ai/v2/errors](https://docs.tupana.ai/v2/errors).

## Reintentos y timeouts

Por defecto el SDK reintenta 2 veces con backoff exponencial y jitter, respetando `Retry-After`:

- `GET`, `PUT` y `DELETE`: ante errores de red, `408`, `429` y `5xx`.
- `POST` y `PATCH` **con** `Idempotency-Key`: igual que arriba.
- `POST` y `PATCH` **sin** `Idempotency-Key`: solo ante `429` y `503`, donde el servidor garantiza que no procesó el request.

```python
tupana = Tupana(max_retries=4, timeout=30.0)
```

## Otros endpoints

Para endpoints v2 sin método propio (folios, libros del SII, sincronización, nómina…) usa `request`, con la misma autenticación, reintentos y errores:

```python
folios = tupana.request("GET", "/folios/", query={"master_entity_id": "ment_4829301923847"})
```

## Configuración

| Parámetro | Variable de entorno | Por defecto |
| --- | --- | --- |
| `api_key` | `TUPANA_API_KEY` | (obligatoria) |
| `base_url` | `TUPANA_BASE_URL` | `https://api.tupana.ai/v2` |
| `timeout` | | `60.0` s |
| `max_retries` | | `2` |
| `default_headers` | | `{}` |
| `http_client` | | un `httpx.Client` / `httpx.AsyncClient` propio (proxies, transportes) |

## Agentes de IA y MCP

Tupana también tiene un servidor MCP remoto en `https://mcp.tupana.ai/mcp` para conectar Claude, ChatGPT, Cursor y otros agentes. Instrucciones en [tupana-ai/tupana-mcp](https://github.com/tupana-ai/tupana-mcp) y un agente que factura con confirmación humana en [tupana-ai/tupana-examples](https://github.com/tupana-ai/tupana-examples).

## Recursos

- Paquete en PyPI: [pypi.org/project/tupana](https://pypi.org/project/tupana/)
- Documentación: [docs.tupana.ai](https://docs.tupana.ai)
- Portal de desarrolladores y API keys: [developers.tupana.ai](https://developers.tupana.ai)
- Servidor MCP: [github.com/tupana-ai/tupana-mcp](https://github.com/tupana-ai/tupana-mcp)
- Ejemplos: [github.com/tupana-ai/tupana-examples](https://github.com/tupana-ai/tupana-examples)
- SDK de Node.js: `npm install tupana` ([npm](https://www.npmjs.com/package/tupana) · [GitHub](https://github.com/tupana-ai/tupana-node))

## Desarrollo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

## Licencia

[MIT](LICENSE)

---

## English summary

Official Python SDK for the [Tupana API v2](https://docs.tupana.ai) — Chilean electronic invoicing (SII DTEs), payment links, invoice factoring (cessions) and webhooks.

```bash
pip install tupana
```

```python
from tupana import Tupana

tupana = Tupana(api_key="...")
batch = tupana.documents.create_batch([invoice], use_defaults=True)
result = tupana.documents.wait_for_batch(batch["batch_id"])
```

Sync and async clients on httpx, `TypedDict` types derived from the OpenAPI v2 spec, automatic retries with backoff on 429/5xx (non-idempotent POSTs are only retried when the server guarantees they were not processed), automatic `Idempotency-Key` on batch issuing, typed errors and webhook signature verification (`X-Pana-Signature`, hex HMAC-SHA256 of the raw body). Python 3.9+. Get an API key at [developers.tupana.ai](https://developers.tupana.ai). MIT licensed.
