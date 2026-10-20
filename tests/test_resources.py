from __future__ import annotations

import json

import respx

from tupana import AsyncTupana, Tupana

from .conftest import BASE


@respx.mock(base_url=BASE)
def test_payment_requests(respx_mock: respx.MockRouter) -> None:
    pr = {"payment_request_id": "pare_1", "status": "pending", "payment_url": "https://x/pagos/t"}
    create = respx_mock.post("/payment-requests/").respond(201, json=pr)
    respx_mock.get("/payment-requests/pare_1/").respond(200, json=pr)
    issue = respx_mock.patch("/payment-requests/pare_1/").respond(
        200, json={**pr, "status": "issued"}
    )
    client = Tupana("k")
    created = client.payment_requests.create(
        {
            "recipient_id": "ment_1",
            "amount": 50000,
            "target_dte_type": 39,
            "dte_recipient": {"rut": "11111111-1", "name": "Juan Soto"},
            "items": [{"description": "Sesión", "quantity": 1, "unit_price": 50000}],
            "external_id": "booking_abc",
        }
    )
    assert created["payment_url"] == "https://x/pagos/t"
    assert client.payment_requests.retrieve("pare_1")["status"] == "pending"
    assert client.payment_requests.issue("pare_1")["status"] == "issued"
    assert json.loads(create.calls.last.request.content)["external_id"] == "booking_abc"
    assert json.loads(issue.calls.last.request.content) == {"status": "issued"}


@respx.mock(base_url=BASE)
def test_cessions(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("/cessions/batch/").respond(
        202, json={"success": True, "status": "processing", "cession_batch_id": "cb_1"}
    )
    respx_mock.get("/cessions/batch/cb_1/").respond(200, json={"id": "cb_1", "status": "completed"})
    client = Tupana("k")
    res = client.cessions.create_batch(
        {
            "master_entity_id": "ment_1",
            "document_ids": ["docu_1"],
            "assignee_rut": "76798398",
            "assignee_dv": "0",
            "assignee_business_name": "Factoring SpA",
            "assignee_address": "Av. Siempre Viva 123",
            "assignee_email": "ops@factoring.cl",
        }
    )
    assert client.cessions.retrieve_batch(res["cession_batch_id"])["status"] == "completed"


@respx.mock(base_url=BASE)
def test_webhooks_connections_entities(respx_mock: respx.MockRouter) -> None:
    create = respx_mock.post("/webhooks/").respond(201, json={"id": "dowe_1"})
    update = respx_mock.patch("/webhooks/dowe_1/").respond(200, json={"id": "dowe_1"})
    delete = respx_mock.delete("/webhooks/dowe_1/").respond(204)
    conns = respx_mock.get("/connections/", params={"search": "acme"}).respond(
        200, json={"data": [], "total": 0, "limit": 25}
    )
    entity = respx_mock.get("/master-entities/", params={"rut": "76543210-K"}).respond(
        200, json={"id": "ment_1"}
    )
    client = Tupana("k")
    client.webhooks.create(
        {
            "master_entity_id": "ment_1",
            "url": "https://example.com/hooks",
            "events": ["document.issued", "payment_request.paid"],
            "secret": "s3cr3t",
        }
    )
    client.webhooks.update("dowe_1", {"is_active": False})
    assert client.webhooks.delete("dowe_1") is None
    client.connections.list(search="acme")
    client.master_entities.lookup("76543210-K")
    for route in (create, update, delete, conns, entity):
        assert route.called


@respx.mock(base_url=BASE)
async def test_async_resources(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("/payment-requests/pare_1/").respond(200, json={"status": "paid"})
    respx_mock.get("/master-entities/").respond(200, json={"id": "ment_1"})
    async with AsyncTupana("k") as client:
        assert (await client.payment_requests.retrieve("pare_1"))["status"] == "paid"
        assert (await client.master_entities.lookup("76543210-K"))["id"] == "ment_1"
