#!/usr/bin/env python3
"""Smoke-check the SonarQube MCP wrapper with readiness-aware stdio transport."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

_INITIALIZE_REQUEST_ID = 1
_TOOLS_LIST_REQUEST_ID = 2
_READY_MARKER = "Status: Server ready"
_STDIO_PROTOCOL_VERSION = "2024-11-05"


@dataclass(frozen=True, slots=True)
class SmokeResult:
    ok: bool
    summary: str
    responses: tuple[dict[str, Any], ...] = ()
    stderr: str = ""
    returncode: int | None = None
    ready_seen: bool = False
    handshake_sent: bool = False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_wrapper_command() -> list[str]:
    return [str(_repo_root() / "scripts/ops/mcp_sonarqube_wrapper.sh")]


def _build_handshake_lines() -> bytes:
    initialize_request = {
        "jsonrpc": "2.0",
        "id": _INITIALIZE_REQUEST_ID,
        "method": "initialize",
        "params": {
            "protocolVersion": _STDIO_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": "bioetl-sonarqube-mcp-smoke",
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
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\n"
        for payload in (
            initialize_request,
            initialized_notification,
            tools_list_request,
        )
    )


def _drain_stdout_frames(
    stdout_buffer: bytearray,
    responses: dict[int, dict[str, Any]],
) -> None:
    while True:
        data = bytes(stdout_buffer)
        if not data:
            return
        if not data.startswith(b"Content-Length:"):
            snippet = data[:120].decode("utf-8", errors="replace")
            raise ValueError(f"Unexpected preamble on MCP stdout: {snippet!r}")
        header_end = data.find(b"\r\n\r\n")
        if header_end == -1:
            return
        header_blob = data[:header_end].decode("ascii", errors="strict")
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
        if len(data) < body_end:
            return
        message = json.loads(data[body_start:body_end].decode("utf-8"))
        if isinstance(message.get("id"), int):
            responses[message["id"]] = message
        del stdout_buffer[:body_end]


def _drain_stdout_lines(
    stdout_buffer: bytearray,
    responses: dict[int, dict[str, Any]],
) -> None:
    while True:
        newline_index = stdout_buffer.find(b"\n")
        if newline_index == -1:
            return
        raw_line = bytes(stdout_buffer[:newline_index]).rstrip(b"\r")
        del stdout_buffer[: newline_index + 1]
        if not raw_line:
            continue
        message = json.loads(raw_line.decode("utf-8"))
        if isinstance(message.get("id"), int):
            responses[message["id"]] = message


def _drain_stdout_messages(
    stdout_buffer: bytearray,
    responses: dict[int, dict[str, Any]],
) -> None:
    data = bytes(stdout_buffer)
    if not data:
        return
    if data.startswith(b"Content-Length:"):
        _drain_stdout_frames(stdout_buffer, responses)
        return
    _drain_stdout_lines(stdout_buffer, responses)


def _find_response(messages: Sequence[dict[str, Any]], request_id: int) -> dict[str, Any] | None:
    for message in messages:
        if message.get("id") == request_id:
            return message
    return None


def run_smoke_command(
    command: Sequence[str],
    *,
    startup_timeout_seconds: float,
    handshake_timeout_seconds: float,
) -> SmokeResult:
    process = subprocess.Popen(
        list(command),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        return SmokeResult(
            ok=False,
            summary="sonarqube MCP smoke could not open process stdio pipes.",
        )

    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")

    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    responses: dict[int, dict[str, Any]] = {}
    ready_seen = False
    handshake_sent = False
    start = time.monotonic()
    ready_deadline = start + startup_timeout_seconds
    handshake_deadline: float | None = None

    try:
        while True:
            now = time.monotonic()
            if not ready_seen and now >= ready_deadline:
                break
            if ready_seen and handshake_deadline is not None and now >= handshake_deadline:
                break
            if ready_seen and _INITIALIZE_REQUEST_ID in responses and _TOOLS_LIST_REQUEST_ID in responses:
                break

            events = selector.select(timeout=1.0)
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    continue
                if key.data == "stderr":
                    stderr_buffer.extend(chunk)
                    stderr_text = stderr_buffer.decode("utf-8", errors="replace")
                    if not ready_seen and _READY_MARKER in stderr_text:
                        ready_seen = True
                        process.stdin.write(_build_handshake_lines())
                        process.stdin.flush()
                        handshake_sent = True
                        handshake_deadline = time.monotonic() + handshake_timeout_seconds
                else:
                    stdout_buffer.extend(chunk)
                    _drain_stdout_messages(stdout_buffer, responses)
    except ValueError as exc:
        return SmokeResult(
            ok=False,
            summary=f"sonarqube MCP smoke received invalid stdout transport output: {exc}",
            responses=tuple(responses.values()),
            stderr=stderr_buffer.decode("utf-8", errors="replace"),
            returncode=process.returncode,
            ready_seen=ready_seen,
            handshake_sent=handshake_sent,
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    response_list = tuple(
        responses[request_id]
        for request_id in sorted(responses)
    )
    initialize_response = _find_response(response_list, _INITIALIZE_REQUEST_ID)
    tools_list_response = _find_response(response_list, _TOOLS_LIST_REQUEST_ID)
    stderr_text = stderr_buffer.decode("utf-8", errors="replace")

    if not ready_seen:
        return SmokeResult(
            ok=False,
            summary=(
                "sonarqube MCP smoke did not observe the server-ready marker on stderr "
                f"within {startup_timeout_seconds:.1f}s."
            ),
            responses=response_list,
            stderr=stderr_text,
            returncode=process.returncode,
            ready_seen=ready_seen,
            handshake_sent=handshake_sent,
        )
    if initialize_response is None or tools_list_response is None:
        return SmokeResult(
            ok=False,
            summary=(
                "sonarqube MCP smoke observed server readiness but did not receive "
                "initialize/tools/list responses over stdio."
            ),
            responses=response_list,
            stderr=stderr_text,
            returncode=process.returncode,
            ready_seen=ready_seen,
            handshake_sent=handshake_sent,
        )
    if "result" not in initialize_response:
        return SmokeResult(
            ok=False,
            summary="sonarqube MCP initialize response did not contain a result payload.",
            responses=response_list,
            stderr=stderr_text,
            returncode=process.returncode,
            ready_seen=ready_seen,
            handshake_sent=handshake_sent,
        )
    if "result" not in tools_list_response:
        return SmokeResult(
            ok=False,
            summary="sonarqube MCP tools/list response did not contain a result payload.",
            responses=response_list,
            stderr=stderr_text,
            returncode=process.returncode,
            ready_seen=ready_seen,
            handshake_sent=handshake_sent,
        )
    tools_payload = tools_list_response["result"]
    if not isinstance(tools_payload, dict) or "tools" not in tools_payload:
        return SmokeResult(
            ok=False,
            summary="sonarqube MCP tools/list response did not expose a tools array.",
            responses=response_list,
            stderr=stderr_text,
            returncode=process.returncode,
            ready_seen=ready_seen,
            handshake_sent=handshake_sent,
        )
    return SmokeResult(
        ok=True,
        summary=(
            "sonarqube MCP smoke observed server readiness and completed "
            "initialize/tools/list over stdio."
        ),
        responses=response_list,
        stderr=stderr_text,
        returncode=process.returncode,
        ready_seen=ready_seen,
        handshake_sent=handshake_sent,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=90.0,
        help="Seconds to wait for the server-ready marker on stderr (default: 90.0)",
    )
    parser.add_argument(
        "--handshake-timeout",
        type=float,
        default=30.0,
        help="Seconds to wait for initialize/tools/list after readiness (default: 30.0)",
    )
    parser.add_argument(
        "--wrapper",
        nargs="+",
        default=_default_wrapper_command(),
        help=(
            "Wrapper command to execute. Defaults to the repo sonarqube wrapper. "
            "Pass a full command after --wrapper to override."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    result = run_smoke_command(
        args.wrapper,
        startup_timeout_seconds=args.startup_timeout,
        handshake_timeout_seconds=args.handshake_timeout,
    )
    stream = sys.stdout if result.ok else sys.stderr
    print(result.summary, file=stream)
    print(
        f"ready_seen={result.ready_seen} handshake_sent={result.handshake_sent} "
        f"responses={len(result.responses)}",
        file=stream,
    )
    if result.stderr:
        print("Captured stderr:", file=stream)
        print(result.stderr.rstrip(), file=stream)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
