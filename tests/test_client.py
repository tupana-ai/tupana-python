from __future__ import annotations

import httpx
import pytest
import respx

from tupana import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    Tupana,
    TupanaError,
    UnprocessableEntityError,
)
from tupana._base import can_retry, clean_query, retry_delay

from .conftest import BASE


def test_requires_api_key() -> None:
    with pytest.raises(TupanaError):
        Tupana()


def test_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TUPANA_API_KEY", "env_key")
    monkeypatch.setenv("TUPANA_BASE_URL", "https://sandbox.example.test/v2/")
    with respx.mock(base_url="https://sandbox.example.test/v2") as mock:
        route = mock.get("/documents/docu_1/").respond(200, json={"id": "docu_1"})
        Tupana().documents.retrieve("docu_1")
    assert route.calls.last.request.headers["authorization"] == "Api-Key env_key"


@respx.mock(base_url=BASE)
def test_sends_headers(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/documents/docu_1/").respond(200, json={"id": "docu_1"})
    client = Tupana("k", default_headers={"X-Extra": "1"})
    assert client.documents.retrieve("docu_1")["id"] == "docu_1"
    headers = route.calls.last.request.headers
    assert headers["authorization"] == "Api-Key k"
    assert headers["user-agent"].startswith("tupana-python/")
    assert headers["x-extra"] == "1"


def test_clean_query() -> None:
    assert clean_query({"a": 1, "b": None, "c": ["33", "34"], "d": True, "e": []}) == {
        "a": 1,
        "c": "33,34",
        "d": "true",
    }


@respx.mock(base_url=BASE)
def test_v2_error_envelope(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("/documents/x/").respond(
        422,
        json={
            "error": {
                "type": "validation_error",
                "code": "parameter_invalid",
                "message": "RUT inválido",
                "param": "documents[0].document_receiver.rut",
                "request_id": "req_abc",
            }
        },
    )
    with pytest.raises(UnprocessableEntityError) as info:
        Tupana("k", max_retries=0).documents.retrieve("x")
    err = info.value
    assert err.status_code == 422
    assert err.code == "parameter_invalid"
    assert err.param == "documents[0].document_receiver.rut"
    assert err.request_id == "req_abc"
    assert str(err) == "RUT inválido"


@respx.mock(base_url=BASE)
def test_flat_errors(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("/documents/batch/b/").respond(404, json={"error": "Batch no encontrado"})
    respx_mock.get("/documents/y/").respond(
        401, json={"error_code": "INVALID_API_KEY", "message": "API key inválida"}
    )
    client = Tupana("k", max_retries=0)
    with pytest.raises(NotFoundError, match="Batch no encontrado"):
        client.documents.retrieve_batch("b")
    with pytest.raises(AuthenticationError) as info:
        client.documents.retrieve("y")
    assert info.value.code == "INVALID_API_KEY"


@respx.mock(base_url=BASE)
def test_retries_429(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/documents/d/")
    route.side_effect = [
        httpx.Response(429, json={"error": "lento"}, headers={"retry-after": "0"}),
        httpx.Response(200, json={"id": "d"}),
    ]
    assert Tupana("k").documents.retrieve("d")["id"] == "d"
    assert route.call_count == 2


@respx.mock(base_url=BASE)
def test_gives_up_after_max_retries(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/documents/d/").respond(429, json={"error": "lento"})
    with pytest.raises(RateLimitError):
        Tupana("k", max_retries=2).documents.retrieve("d")
    assert route.call_count == 3


@respx.mock(base_url=BASE)
def test_post_without_key_not_retried_on_500(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post("/payment-requests/").respond(500, json={"error": "boom"})
    with pytest.raises(InternalServerError):
        Tupana("k").payment_requests.create({"recipient_id": "ment_1", "amount": 1000})
    assert route.call_count == 1


@respx.mock(base_url=BASE)
def test_post_without_key_retried_on_503(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post("/payment-requests/")
    route.side_effect = [
        httpx.Response(503, json={"error": "ocupado", "code": "server_busy"}),
        httpx.Response(201, json={"payment_request_id": "pare_1", "status": "pending"}),
    ]
    pr = Tupana("k").payment_requests.create({"recipient_id": "ment_1", "amount": 1000})
    assert pr["status"] == "pending"
    assert route.call_count == 2


@respx.mock(base_url=BASE)
def test_connection_and_timeout_errors(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("/documents/a/").mock(side_effect=httpx.ConnectError("boom"))
    respx_mock.get("/documents/b/").mock(side_effect=httpx.ReadTimeout("slow"))
    client = Tupana("k", max_retries=1)
    with pytest.raises(APIConnectionError):
        client.documents.retrieve("a")
    with pytest.raises(APITimeoutError):
        client.documents.retrieve("b")


def test_retry_policy() -> None:
    assert can_retry("GET", None, 500)
    assert can_retry("GET", None, None)
    assert not can_retry("POST", None, 500)
    assert not can_retry("POST", None, None)
    assert can_retry("POST", None, 429)
    assert can_retry("POST", "key", 502)
    assert not can_retry("GET", None, 400)


def test_retry_delay_respects_header() -> None:
    assert retry_delay(0, httpx.Headers({"retry-after": "3"})) == 3.0
    assert 0.5 <= retry_delay(0) <= 0.625
    assert retry_delay(20) <= 10.0


@respx.mock(base_url=BASE)
def test_raw_request(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/folios/", params={"master_entity_id": "ment_1"}).respond(
        200, json={"data": []}
    )
    Tupana("k").request("GET", "/folios/", query={"master_entity_id": "ment_1"})
    assert route.called


def test_context_manager_closes() -> None:
    with Tupana("k") as client:
        assert client.base_url == BASE
    assert client._http.is_closed
