from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from tupana import MAX_BATCH_SIZE, AsyncTupana, BatchTimeoutError, Tupana, TupanaError

from .conftest import BASE, INVOICE

CREATED = {
    "batch_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "created_at": "2026-10-20T10:00:00Z",
    "documents": [{"index": 0, "status": "created", "document": {"id": "docu_1"}}],
}


@respx.mock(base_url=BASE)
def test_create_batch_headers_and_body(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post("/documents/batch/").respond(201, json=CREATED)
    res = Tupana("k").documents.create_batch(
        [INVOICE], use_defaults=True, idempotency_key="pedido-123"
    )
    assert res["batch_id"] == CREATED["batch_id"]
    req = route.calls.last.request
    assert req.headers["x-use-defaults"] == "true"
    assert req.headers["idempotency-key"] == "pedido-123"
    assert req.headers["content-type"] == "application/json"
    assert json.loads(req.content) == {"documents": [INVOICE]}


@respx.mock(base_url=BASE)
def test_create_batch_auto_idempotency_key_reused_on_retry(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post("/documents/batch/")
    route.side_effect = [
        httpx.Response(500, json={"error": "boom"}),
        httpx.Response(202, json=CREATED),
    ]
    Tupana("k").documents.create_batch([INVOICE])
    assert route.call_count == 2
    first = route.calls[0].request.headers["idempotency-key"]
    assert len(first) == 36
    assert route.calls[1].request.headers["idempotency-key"] == first


@respx.mock(base_url=BASE)
def test_create_batch_draft(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post("/documents/batch/").respond(201, json={"documents": []})
    Tupana("k").documents.create_batch([INVOICE], state="draft", preview=True)
    body = json.loads(route.calls.last.request.content)
    assert body["state"] == "draft"
    assert body["preview"] is True


def test_create_batch_validates_size() -> None:
    client = Tupana("k")
    with pytest.raises(TupanaError):
        client.documents.create_batch([])
    with pytest.raises(TupanaError):
        client.documents.create_batch([INVOICE] * (MAX_BATCH_SIZE + 1))  # type: ignore[list-item]


@respx.mock(base_url=BASE)
def test_wait_for_batch(respx_mock: respx.MockRouter) -> None:
    batch_id = CREATED["batch_id"]
    processing = {"id": batch_id, "status": "processing", "documents": []}
    done = {
        "id": batch_id,
        "status": "completed",
        "documents": [{"index": 0, "status": "success", "document": {"folio": "1234"}}],
    }
    route = respx_mock.get(f"/documents/batch/{batch_id}/")
    route.side_effect = [
        httpx.Response(200, json=processing),
        httpx.Response(200, json=processing),
        httpx.Response(200, json=done),
    ]
    seen: list[str] = []
    batch = Tupana("k").documents.wait_for_batch(
        batch_id, interval=0.001, on_poll=lambda b: seen.append(str(b["status"]))
    )
    assert batch["status"] == "completed"
    assert seen == ["processing", "processing"]


@respx.mock(base_url=BASE)
def test_wait_for_batch_timeout(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("/documents/batch/b/").respond(
        200, json={"id": "b", "status": "processing", "documents": []}
    )
    with pytest.raises(BatchTimeoutError):
        Tupana("k").documents.wait_for_batch("b", interval=0.01, timeout=0.001)


@respx.mock(base_url=BASE)
def test_list_filters(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/documents/").respond(200, json={"data": [], "meta": {}, "links": {}})
    Tupana("k").documents.list(
        "ment_1",
        document_type="issued",
        dte_type__code__in=["33", "34"],
        issue_date_gte="2026-01-01",
        json_param={"external_order_id": "PED-123"},
    )
    params = route.calls.last.request.url.params
    assert params["master_entity_id"] == "ment_1"
    assert params["dte_type__code__in"] == "33,34"
    assert params["json_param__external_order_id"] == "PED-123"
    assert params["issue_date_gte"] == "2026-01-01"
    assert "page" not in params


def _page(n: int, ids: list[str]) -> httpx.Response:
    body: dict[str, Any] = {
        "data": [{"id": i} for i in ids],
        "meta": {"page": n, "page_size": 2, "total": 3, "total_pages": 2},
        "links": {"next": None, "prev": None},
    }
    return httpx.Response(200, json=body)


@respx.mock(base_url=BASE)
def test_list_auto_paging(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/documents/")
    route.side_effect = [_page(1, ["a", "b"]), _page(2, ["c"])]
    ids = [d["id"] for d in Tupana("k").documents.list_auto_paging("m", page_size=2)]
    assert ids == ["a", "b", "c"]
    assert route.calls[1].request.url.params["page"] == "2"


@respx.mock(base_url=BASE)
async def test_async_client(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/documents/batch/").respond(201, json=CREATED)
    route = respx_mock.get("/documents/")
    route.side_effect = [_page(1, ["a", "b"]), _page(2, ["c"])]
    async with AsyncTupana("k") as client:
        res = await client.documents.create_batch([INVOICE], use_defaults=True)
        assert res["batch_id"] == CREATED["batch_id"]
        ids = [d["id"] async for d in client.documents.list_auto_paging("m")]
    assert ids == ["a", "b", "c"]
