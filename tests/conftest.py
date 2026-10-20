from __future__ import annotations

from collections.abc import Iterator

import pytest

BASE = "https://api.tupana.ai/v2"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("TUPANA_API_KEY", raising=False)
    monkeypatch.delenv("TUPANA_BASE_URL", raising=False)
    # Sin esperas reales entre reintentos.
    monkeypatch.setattr("tupana._client.retry_delay", lambda *a, **k: 0.0)
    yield


INVOICE = {
    "dte_type": {"code": "33"},
    "document_issuer": {"rut": "76543210-K"},
    "document_receiver": {"rut": "77777777-7"},
    "details": [{"item_name": "Asesoría", "quantity": 1, "unit_price": 100000}],
}
