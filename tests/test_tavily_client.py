"""Tests for TavilyClient retry logic and caching.

These tests mock the HTTP client via injectable factory to avoid real calls.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.core.llm_client import TavilyClient


class _MockHTTPClient:
    """Mock httpx.Client that never closes and can produce multiple responses."""

    def __init__(self, responses):  # noqa: D401
        self._responses = list(responses)
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Do not actually close; allow reuse across retries
        return False

    def post(self, url: str, headers: dict[str, str], json: dict[str, Any]):  # noqa: D401
        """Simulate POST returning a mock Response object."""
        self.calls += 1
        action = self._responses.pop(0)
        if action[0] == "error":
            # Simulate an HTTP status error
            import httpx

            status = action[1]

            class _Resp:
                def __init__(self, st):
                    self.status_code = st
                    self.request = None
                    self.headers = {}  # Add headers for Retry-After logic

                def raise_for_status(self):
                    raise httpx.HTTPStatusError(
                        "stub error", request=httpx.Request("POST", url), response=self
                    )

            resp = _Resp(status)
            resp.raise_for_status()
        if action[0] == "success":
            data = action[1]

            class _Resp:
                def __init__(self, payload):
                    self._payload = payload

                def raise_for_status(self):
                    pass

                def json(self):
                    return self._payload

            return _Resp(data)
        raise RuntimeError(f"Unexpected stub action: {action!r}")


def test_tavily_retry_success(monkeypatch):
    """Should retry after 429 then succeed and return data for each field."""
    os.environ["TAVILY_MAX_RETRIES"] = "2"
    stub = _MockHTTPClient([
        ("error", 429),
        ("success", {"answer": "Example answer", "results": []}),
    ])

    def factory(timeout):
        return stub

    client = TavilyClient(http_client_factory=factory)
    result = client.search_online_for_missing_fields(
        product_name="Acetona",
        cas_number="67-64-1",
        un_number="1090",
        missing_fields=["fabricante"],
    )
    assert str(result["fabricante"]["value"]).startswith("Example")
    assert stub.calls == 2  # one retry + success


def test_tavily_in_memory_cache(monkeypatch):
    """Second identical query should hit in-memory cache."""
    os.environ["TAVILY_MAX_RETRIES"] = "1"
    stub = _MockHTTPClient([("success", {"answer": "Cache answer", "results": []})])

    def factory(timeout):
        return stub

    client = TavilyClient(http_client_factory=factory)
    first = client.search_online_for_missing_fields(
        product_name="Ethanol",
        cas_number="64-17-5",
        un_number="1170",
        missing_fields=["fabricante"],
    )
    second = client.search_online_for_missing_fields(
        product_name="Ethanol",
        cas_number="64-17-5",
        un_number="1170",
        missing_fields=["fabricante"],
    )
    assert first == second
    assert stub.calls == 1  # second call served from cache


def test_tavily_persistent_cache(tmp_path: Path, monkeypatch):
    """Persistent cache serves data across instances without new HTTP calls."""
    # Enable persistent cache with temp DB path
    db_path = tmp_path / "tavily_cache.db"
    os.environ["TAVILY_PERSIST_CACHE"] = "1"
    os.environ["TAVILY_CACHE_DB_PATH"] = str(db_path)
    # First client performs a network success
    stub1 = _MockHTTPClient([("success", {"answer": "Persistent answer", "results": []})])

    def factory1(timeout):
        return stub1

    client1 = TavilyClient(http_client_factory=factory1)
    r1 = client1.search_online_for_missing_fields(
        product_name="Benzeno",
        cas_number="71-43-2",
        un_number="1114",
        missing_fields=["fabricante"],
    )
    assert stub1.calls == 1
    # Second client should load from persistent cache; provide stub that would
    # error if used
    stub2 = _MockHTTPClient([("error", 429)])

    def factory2(timeout):
        return stub2

    client2 = TavilyClient(http_client_factory=factory2)
    r2 = client2.search_online_for_missing_fields(
        product_name="Benzeno",
        cas_number="71-43-2",
        un_number="1114",
        missing_fields=["fabricante"],
    )
    assert r1 == r2
    # Because cache hit, stub2 should not be called
    assert stub2.calls == 0
