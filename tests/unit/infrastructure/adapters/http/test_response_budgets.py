"""Bound decompression output before allocating an oversized provider response."""

import gzip
import httpx
import pytest
from bioetl.infrastructure.adapters.http import request_timing as timing

pytestmark = pytest.mark.unit


class Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False
        self.read = 0

    async def __aiter__(self):
        for chunk in self.chunks:
            self.read += 1
            yield chunk

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "encoding,data,wire,decoded",
    [
        ("identity", b"x" * 101, 100, 1000),
        ("identity", b"x" * 101, 1000, 100),
        ("gzip", gzip.compress(b"x" * 10000), 1000, 100),
    ],
)
async def test_overflow_closes_stream_and_stops_before_next_chunk(
    monkeypatch, encoding, data, wire, decoded
):
    monkeypatch.setattr(timing, "_MAX_RESPONSE_WIRE_BYTES", wire)
    monkeypatch.setattr(timing, "_MAX_RESPONSE_DECODED_BYTES", decoded)
    stream = Chunks([data, b"unused"])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, headers={"Content-Encoding": encoding}, stream=stream
            )
        )
    ) as client:
        with pytest.raises(timing.ResponseBudgetExceeded):
            await timing._dispatch_http_request(
                client,
                "GET",
                "https://provider.example",
                {},
                is_stream=False,
                request_timeout=1,
            )
    assert stream.closed and stream.read == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("encoding", ["identity", "gzip", "deflate"])
async def test_valid_response_at_decoded_limit(monkeypatch, encoding):
    import zlib

    data = b'{"ok":true}'
    monkeypatch.setattr(timing, "_MAX_RESPONSE_DECODED_BYTES", len(data))
    raw = (
        data
        if encoding == "identity"
        else (gzip.compress(data) if encoding == "gzip" else zlib.compress(data))
    )
    stream = Chunks([raw[:3], raw[3:]])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, headers={"Content-Encoding": encoding}, stream=stream
            )
        )
    ) as client:
        response = await timing._dispatch_http_request(
            client,
            "GET",
            "https://provider.example",
            {},
            is_stream=False,
            request_timeout=1,
        )
    assert response.json() == {"ok": True}
    assert stream.closed


@pytest.mark.asyncio
async def test_oversized_response_is_not_retried(monkeypatch):
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

    monkeypatch.setattr(timing, "_MAX_RESPONSE_DECODED_BYTES", 10)
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(
            200, headers={"Content-Length": "1"}, stream=Chunks([b"x" * 11])
        )

    client = UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(100, 1),
        circuit_breaker=CircuitBreakerGuard(provider="audit"),
        provider="audit",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        with pytest.raises(timing.ResponseBudgetExceeded):
            await client.get("https://provider.example")
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_timeout_closes_inflight_response():
    import asyncio

    class Slow(Chunks):
        async def __aiter__(self):
            await asyncio.sleep(10)
            yield b"unused"

    stream = Slow([])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))
    ) as client:
        with pytest.raises(TimeoutError):
            await timing._dispatch_http_request(
                client,
                "GET",
                "https://provider.example",
                {},
                is_stream=False,
                request_timeout=0.01,
            )
    assert stream.closed
