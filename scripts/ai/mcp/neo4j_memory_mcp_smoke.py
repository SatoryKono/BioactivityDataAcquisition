#!/usr/bin/env python3
"""Smoke-check the neo4j-memory MCP wrapper through real stdio framing."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_INITIALIZE_REQUEST_ID = 1
_TOOLS_LIST_REQUEST_ID = 2


@dataclass(frozen=True, slots=True)
class SmokeResult:
    ok: bool
    summary: str
    responses: tuple[dict[str, Any], ...] = ()
    stderr: str = ""
    returncode: int | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_wrapper_command() -> list[str]:
    return [str(_repo_root() / "scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh")]


def _encode_frame(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def _parse_frames(data: bytes) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(data):
        if not data[cursor:].startswith(b"Content-Length:"):
            snippet = data[cursor : cursor + 80].decode("utf-8", errors="replace")
            raise ValueError(f"Unexpected preamble on MCP stdout: {snippet!r}")
        header_end = data.find(b"\r\n\r\n", cursor)
        if header_end == -1:
            raise ValueError("Incomplete MCP frame header.")
        header_blob = data[cursor:header_end].decode("ascii", errors="strict")
        headers: dict[str, str] = {}
        for line in header_blob.split("\r\n"):
            name, _, value = line.partition(":")
            if not _:
                raise ValueError(f"Malformed MCP header line: {line!r}")
            headers[name.strip().lower()] = value.strip()
        content_length_raw = headers.get("content-length")
        if content_length_raw is None:
            raise ValueError("MCP frame is missing Content-Length header.")
        content_length = int(content_length_raw)
        body_start = header_end + 4
        body_end = body_start + content_length
        body = data[body_start:body_end]
        if len(body) != content_length:
            raise ValueError("Incomplete MCP frame body.")
        messages.append(json.loads(body.decode("utf-8")))
        cursor = body_end
    return messages


def _build_handshake() -> bytes:
    initialize_request = {
        "jsonrpc": "2.0",
        "id": _INITIALIZE_REQUEST_ID,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "bioetl-neo4j-memory-smoke",
                "version": "1.0",
            },
        },
    }
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    tools_list_request = {
        "jsonrpc": "2.0",
        "id": _TOOLS_LIST_REQUEST_ID,
        "method": "tools/list",
        "params": {},
    }
    return b"".join(
        [
            _encode_frame(initialize_request),
            _encode_frame(initialized_notification),
            _encode_frame(tools_list_request),
        ]
    )


def _find_response(messages: Sequence[dict[str, Any]], request_id: int) -> dict[str, Any] | None:
    for message in messages:
        if message.get("id") == request_id:
            return message
    return None


def _to_bytes(payload: bytes | str | None) -> bytes:
    if payload is None:
        return b""
    if isinstance(payload, bytes):
        return payload
    return payload.encode("utf-8", errors="replace")


def _has_complete_handshake(responses: Sequence[dict[str, Any]]) -> bool:
    initialize_response = _find_response(responses, _INITIALIZE_REQUEST_ID)
    tools_list_response = _find_response(responses, _TOOLS_LIST_REQUEST_ID)
    if initialize_response is None or tools_list_response is None:
        return False
    if "result" not in initialize_response or "result" not in tools_list_response:
        return False
    tools_payload = tools_list_response["result"]
    return isinstance(tools_payload, dict) and "tools" in tools_payload


def run_smoke_command(
    command: Sequence[str],
    *,
    timeout_seconds: float,
) -> SmokeResult:
    process = subprocess.Popen(
        list(command),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(
            input=_build_handshake(),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        partial_stdout = _to_bytes(exc.output)
        partial_stderr = _to_bytes(exc.stderr)
        process.kill()
        stdout, stderr = process.communicate()
        stdout = partial_stdout + _to_bytes(stdout)
        stderr = partial_stderr + _to_bytes(stderr)
        try:
            responses = tuple(_parse_frames(stdout))
        except ValueError as parse_exc:
            return SmokeResult(
                ok=False,
                summary=(
                    "neo4j-memory MCP smoke received invalid framed output: "
                    f"{parse_exc}"
                ),
                stderr=stderr.decode("utf-8", errors="replace"),
                returncode=process.returncode,
            )
        if _has_complete_handshake(responses):
            return SmokeResult(
                ok=True,
                summary=(
                    "neo4j-memory MCP smoke completed initialize/tools/list over framed stdio."
                ),
                responses=responses,
                stderr=stderr.decode("utf-8", errors="replace"),
                returncode=0,
            )
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP smoke timed out before initialize/tools/list completed.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )

    try:
        responses = tuple(_parse_frames(stdout))
    except ValueError as exc:
        return SmokeResult(
            ok=False,
            summary=f"neo4j-memory MCP smoke received invalid framed output: {exc}",
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )

    initialize_response = _find_response(responses, _INITIALIZE_REQUEST_ID)
    tools_list_response = _find_response(responses, _TOOLS_LIST_REQUEST_ID)
    if initialize_response is None:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP smoke did not receive an initialize response.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    if tools_list_response is None:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP smoke did not receive a tools/list response.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    if "result" not in initialize_response:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP initialize response did not contain a result payload.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    if "result" not in tools_list_response:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP tools/list response did not contain a result payload.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    tools_payload = tools_list_response["result"]
    if not isinstance(tools_payload, dict) or "tools" not in tools_payload:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP tools/list response did not expose a tools array.",
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    if process.returncode != 0:
        return SmokeResult(
            ok=False,
            summary=(
                "neo4j-memory MCP smoke completed the handshake but the wrapper exited "
                f"with code {process.returncode}."
            ),
            responses=responses,
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=process.returncode,
        )
    return SmokeResult(
        ok=True,
        summary=(
            "neo4j-memory MCP smoke completed initialize/tools/list over framed stdio."
        ),
        responses=responses,
        stderr=stderr.decode("utf-8", errors="replace"),
        returncode=process.returncode,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Smoke-check timeout in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--wrapper",
        nargs="+",
        default=_default_wrapper_command(),
        help=(
            "Wrapper command to execute. Defaults to the repo neo4j-memory wrapper. "
            "Pass a full command after --wrapper to override."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    result = run_smoke_command(args.wrapper, timeout_seconds=args.timeout)
    stream = sys.stdout if result.ok else sys.stderr
    print(result.summary, file=stream)
    if result.stderr:
        print("Captured stderr:", file=stream)
        print(result.stderr.rstrip(), file=stream)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
