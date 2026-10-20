from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional

if TYPE_CHECKING:
    from .._client import AsyncTupana, Tupana


class SyncResource:
    def __init__(self, client: Tupana) -> None:
        self._client = client


class AsyncResource:
    def __init__(self, client: AsyncTupana) -> None:
        self._client = client


def compact(values: Mapping[str, Any]) -> Dict[str, Any]:
    """Quita los valores ``None`` de un dict de parámetros."""
    return {k: v for k, v in values.items() if v is not None}


def has_next_page(page: Mapping[str, Any], current: int) -> bool:
    data = page.get("data") or []
    if not data:
        return False
    meta: Mapping[str, Any] = page.get("meta") or {}
    total_pages: Optional[int] = meta.get("total_pages")
    if total_pages is not None:
        return current < int(total_pages)
    links: Mapping[str, Any] = page.get("links") or {}
    return bool(links.get("next"))
