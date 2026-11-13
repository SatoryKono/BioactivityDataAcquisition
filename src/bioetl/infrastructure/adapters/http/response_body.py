"""Bound HTTP wire reads and decompression before response materialization."""

from __future__ import annotations

import zlib

import httpx


class ResponseBudgetExceeded(ValueError):
    """Response exceeds the non-retryable transport memory budget."""


class _DeflateDecoder:
    """Keep HTTPX's initial raw-DEFLATE fallback with bounded decoder output."""

    def __init__(self) -> None:
        self._decoder = zlib.decompressobj(zlib.MAX_WBITS)
        self._first = True
        self._prefix = b""

    def decompress(self, data: bytes, max_length: int) -> bytes:
        if not self._first:
            return self._decoder.decompress(data, max_length)
        # A fragmented zlib header must not consume the one initial fallback.
        # This pending prefix contains at most one byte, never an entire body.
        data = self._prefix + data
        if len(data) < 2:
            self._prefix = data
            return b""
        self._prefix = b""
        self._first = False
        try:
            return self._decoder.decompress(data, max_length)
        except zlib.error:
            self._decoder = zlib.decompressobj(-zlib.MAX_WBITS)
            return self._decoder.decompress(data, max_length)

    @property
    def eof(self) -> bool:
        return self._decoder.eof

    @property
    def unused_data(self) -> bytes:
        return self._decoder.unused_data


async def read_bounded_response(
    response: httpx.Response, *, wire_limit: int, decoded_limit: int
) -> httpx.Response:
    """Bound raw reads and decompressor output before materializing JSON input."""
    if (
        response.request.method == "HEAD"
        or response.status_code in {204, 304}
        or 100 <= response.status_code < 200
    ):
        return await _read_bodyless_response(
            response, wire_limit=wire_limit, decoded_limit=decoded_limit
        )
    if response.is_stream_consumed:
        if len(response.content) > decoded_limit:
            raise ResponseBudgetExceeded("Decoded HTTP response budget exceeded")
        return response
    encoding = response.headers.get("Content-Encoding", "identity").lower().strip()
    if encoding not in {"identity", "gzip", "deflate"}:
        raise httpx.DecodingError(
            "Unsupported HTTP response content encoding", request=response.request
        )
    body, wire_bytes = await _collect_response_body(
        response, encoding, wire_limit=wire_limit, decoded_limit=decoded_limit
    )
    headers = response.headers.copy()
    headers.pop("content-encoding", None)
    headers["Content-Length"] = str(len(body))
    response.extensions["bioetl_wire_response_bytes"] = wire_bytes
    return httpx.Response(
        response.status_code,
        headers=headers,
        content=bytes(body),
        request=response.request,
        extensions=response.extensions,
        history=response.history,
    )


async def _read_bodyless_response(
    response: httpx.Response, *, wire_limit: int, decoded_limit: int
) -> httpx.Response:
    """Consume protocol EOF without decoding or changing representation headers."""
    wire_bytes = 0
    if not response.is_stream_consumed:
        _, wire_bytes = await _collect_response_body(
            response, "identity", wire_limit=wire_limit, decoded_limit=decoded_limit
        )
    result = httpx.Response(
        response.status_code,
        content=b"",
        request=response.request,
        extensions=dict(response.extensions),
        history=response.history,
    )
    result.headers = response.headers.copy()
    result.extensions["bioetl_wire_response_bytes"] = wire_bytes
    return result


def _response_body_decoder(encoding: str, window_bits: int):
    """Select identity, gzip, or raw-DEFLATE decoder without nested ternaries."""
    if encoding == "identity":
        return None
    if encoding == "deflate":
        return _DeflateDecoder()
    return zlib.decompressobj(window_bits)


async def _collect_response_body(
    response: httpx.Response, encoding: str, *, wire_limit: int, decoded_limit: int
) -> tuple[bytes, int]:
    """Read bounded chunks without allocating an unbounded decoder output."""
    window_bits = 16 + zlib.MAX_WBITS if encoding == "gzip" else zlib.MAX_WBITS
    decoder = _response_body_decoder(encoding, window_bits)
    body = bytearray()
    wire_bytes = 0
    try:
        async for raw in response.aiter_raw():
            wire_bytes += len(raw)
            if wire_bytes > wire_limit:
                raise ResponseBudgetExceeded("Wire HTTP response budget exceeded")
            remaining = decoded_limit - len(body)
            decoded = raw if decoder is None else decoder.decompress(raw, remaining + 1)
            if len(decoded) > remaining:
                raise ResponseBudgetExceeded("Decoded HTTP response budget exceeded")
            body.extend(decoded)
            if decoder is not None and decoder.unused_data:
                raise httpx.DecodingError(
                    "Trailing or concatenated compressed HTTP response",
                    request=response.request,
                )
    except zlib.error as exc:
        raise httpx.DecodingError(
            "Invalid compressed HTTP response", request=response.request
        ) from exc
    if decoder is not None and not decoder.eof:
        raise httpx.DecodingError(
            "Truncated compressed HTTP response", request=response.request
        )
    return bytes(body), wire_bytes
