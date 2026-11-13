"""Bound decompression output before allocating an oversized provider response."""

from __future__ import annotations

import gzip
import zlib
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


@pytest.mark.asyncio
@pytest.mark.parametrize("encoding", ["gzip", "deflate", "br", "identity"])
@pytest.mark.parametrize("length", [None, "123456"])
async def test_bodyless_head_keeps_representation_headers(
    monkeypatch, encoding, length
):
    def forbidden_decoder(*args, **kwargs):
        raise AssertionError("A bodyless response must not instantiate a decoder")

    monkeypatch.setattr(zlib, "decompressobj", forbidden_decoder)
    headers = {"Content-Encoding": encoding, "ETag": '"representation-tag"'}
    if length is not None:
        headers["Content-Length"] = length
    stream = Chunks([])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, headers=headers, stream=stream)
        )
    ) as client:
        response = await timing._dispatch_http_request(
            client,
            "HEAD",
            "https://provider.example",
            {},
            is_stream=False,
            request_timeout=1,
        )
    assert response.content == b""
    assert dict(response.headers) == {k.lower(): v for k, v in headers.items()}
    assert stream.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [204, 304])
@pytest.mark.parametrize("encoding", ["gzip", "deflate"])
async def test_bodyless_status_keeps_representation_metadata(status, encoding):
    headers = {"Content-Encoding": encoding, "ETag": '"representation-tag"'}
    if status == 304:
        headers["Content-Length"] = "123456"
    stream = Chunks([])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(status, headers=headers, stream=stream)
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
    assert response.content == b""
    assert dict(response.headers) == {k.lower(): v for k, v in headers.items()}
    assert stream.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("encoding", ["gzip", "deflate"])
async def test_corrupt_compression_is_counted_by_breaker_and_health_contract(encoding):
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
    from bioetl.infrastructure.adapters.health_check_contract import HEALTH_CHECK_ERRORS

    stream = Chunks([b"not a compressed response"])
    breaker = CircuitBreakerGuard(provider="audit")
    client = UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(100, 1),
        circuit_breaker=breaker,
        provider="audit",
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, headers={"Content-Encoding": encoding}, stream=stream
            )
        )
    ) as transport:
        client._client = transport
        with pytest.raises(httpx.DecodingError) as caught:
            await client.get_once("https://provider.example")
    assert isinstance(caught.value, HEALTH_CHECK_ERRORS)
    assert caught.value.request.url == "https://provider.example"
    assert breaker.get_failure_count() == 1
    assert stream.closed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "encoding,raw",
    [
        ("gzip", gzip.compress(b"payload")[:-3]),
        ("gzip", gzip.compress(b"a") + gzip.compress(b"b")),
        ("unsupported", b"payload"),
    ],
)
async def test_malformed_codec_conditions_have_httpx_error_contract(encoding, raw):
    stream = Chunks([raw])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, headers={"Content-Encoding": encoding}, stream=stream
            )
        )
    ) as client:
        with pytest.raises(httpx.DecodingError):
            await timing._dispatch_http_request(
                client,
                "GET",
                "https://provider.example",
                {},
                is_stream=False,
                request_timeout=1,
            )
    assert stream.closed
