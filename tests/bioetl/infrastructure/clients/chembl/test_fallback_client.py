from types import SimpleNamespace

from bioetl.domain.clients.base.contracts import RateLimiterABC, ResponseParserABC
from bioetl.infrastructure.clients.chembl.impl.chembl_http_client_impl import (
    ChemblHttpClientImpl,
)
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilderImpl,
)


class DummyParser(ResponseParserABC):
    def parse_response(self, raw_response):
        return []

    def extract_metadata(self, raw_response):
        return {}


class DummyLimiter(RateLimiterABC):
    def acquire(self) -> None:
        return None

    def wait_if_needed(self) -> None:
        return None


class DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_fallback_switch_on_500(monkeypatch):
    builder = ChemblRequestBuilderImpl(base_url="https://api.example")

    # http.request will return 500 for primary, 200 for fallback
    calls = {"activity": 0}

    def fake_request(method: str, url: str, **kwargs):
        if "/activity.json" in url:
            calls["activity"] += 1
            return DummyResponse(500, {"error": "server"})
        return DummyResponse(
            200, {"page_meta": {"limit": 1, "offset": 0, "total_count": 1}}
        )

    http = SimpleNamespace(request=fake_request)

    client = ChemblHttpClientImpl(
        request_builder=builder,
        response_parser=DummyParser(),
        rate_limiter=DummyLimiter(),
        client=http,
        fallbacks={"activity": ["activity", "activity_archive"]},
    )

    result = client.fetch("activity", limit=1)
    assert isinstance(result, dict)
    assert client.get_last_endpoint_used() == "activity_archive"
    assert calls["activity"] >= 1
