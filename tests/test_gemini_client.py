import json
from types import SimpleNamespace

import pytest

from src.core.llm_client import GeminiClient


class DummyResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class DummyClient:
    def __init__(self, data):
        self._data = data
        self.post_calls = []

    def post(self, url, params=None, headers=None, json=None):  # noqa: A002 - shadowing ok in test
        self.post_calls.append({"url": url, "params": params, "headers": headers, "json": json})
        return DummyResponse(self._data)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_gemini_client_parses_json(monkeypatch):
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "numero_onu": {"value": "1203", "confidence": 0.8, "source": "https://example.com"},
                                "numero_cas": {"value": "67-56-1", "confidence": 0.9, "source": "https://pubchem.ncbi.nlm.nih.gov"},
                            })
                        }
                    ]
                }
            }
        ]
    }

    import src.core.llm_client as llm_mod

    # Patch httpx.Client to our dummy
    monkeypatch.setattr(llm_mod.httpx, "Client", lambda timeout: DummyClient(data))

    client = GeminiClient()
    # Force api_key present for test_connection
    client.api_key = "test-key"

    res = client.search_online_for_missing_fields(
        product_name="Metanol",
        cas_number="67-56-1",
        un_number=None,
        missing_fields=["numero_onu", "numero_cas"],
    )

    assert res["numero_onu"]["value"] == "1203"
    assert res["numero_cas"]["value"] == "67-56-1"
    # Confidence is a numeric value; content validated by keys above
