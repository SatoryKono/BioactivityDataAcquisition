#!/usr/bin/env python3
"""Smoke-check the neo4j-memory MCP wrapper through real stdio framing."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from typing import Any

_INITIALIZE_REQUEST_ID = 1
_TOOLS_LIST_REQUEST_ID = 2
_SUCCESS_SUMMARY = (
    "neo4j-memory MCP smoke completed initialize/tools/list over framed stdio."
)
_INVALID_FRAMED_OUTPUT_SUMMARY = (
    "neo4j-memory MCP smoke received invalid framed output: "
)
_HANDSHAKE_EXITED_SUMMARY = (
    "neo4j-memory MCP smoke completed the handshake but the wrapper exited "
)


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


def _read_frame(stream: Any) -> dict[str, Any] | None:
    line = stream.readline()
    if not line:
        return None
    if not line.startswith(b"Content-Length:"):
        snippet = line[:80].decode("utf-8", errors="replace")
        raise ValueError(f"Unexpected preamble on MCP stdout: {snippet!r}")

    header_lines = [line]
    while True:
        header_line = stream.readline()
        if not header_line:
            raise ValueError("Incomplete MCP frame header.")
        if header_line in {b"\r\n", b"\n"}:
            break
        header_lines.append(header_line)

    headers: dict[str, str] = {}
    for header_line in header_lines:
        line_text = header_line.decode("ascii", errors="strict").rstrip("\r\n")
        name, sep, value = line_text.partition(":")
        if not sep:
            raise ValueError(f"Malformed MCP header line: {line_text!r}")
        headers[name.strip().lower()] = value.strip()

    content_length_raw = headers.get("content-length")
    if content_length_raw is None:
        raise ValueError("MCP frame is missing Content-Length header.")
    content_length = int(content_length_raw)
    body = stream.read(content_length)
    if len(body) != content_length:
        raise ValueError("Incomplete MCP frame body.")
    return json.loads(body.decode("utf-8"))


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


def _find_response(
    messages: Sequence[dict[str, Any]], request_id: int
) -> dict[str, Any] | None:
    for message in messages:
        if message.get("id") == request_id:
            return message
    return None


def _has_complete_handshake(responses: Sequence[dict[str, Any]]) -> bool:
    initialize_response = _find_response(responses, _INITIALIZE_REQUEST_ID)
    tools_list_response = _find_response(responses, _TOOLS_LIST_REQUEST_ID)
    if initialize_response is None or tools_list_response is None:
        return False
    if "result" not in initialize_response or "result" not in tools_list_response:
        return False
    tools_payload = tools_list_response["result"]
    return isinstance(tools_payload, dict) and "tools" in tools_payload


def _read_frames_until_eof(
    stream: Any,
    responses: Queue[dict[str, Any] | ValueError],
) -> None:
    try:
        while True:
            message = _read_frame(stream)
            if message is None:
                return
            responses.put(message)
    except ValueError as exc:
        responses.put(exc)


def _read_stderr_until_eof(stream: Any, chunks: list[bytes]) -> None:
    for chunk in iter(lambda: stream.readline(), b""):
        chunks.append(chunk)


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2.0)


def _drain_response_queue(
    response_queue: Queue[dict[str, Any] | ValueError],
    responses: list[dict[str, Any]],
) -> ValueError | None:
    while True:
        try:
            item = response_queue.get_nowait()
        except Empty:
            return None
        if isinstance(item, ValueError):
            return item
        responses.append(item)


def _stderr_text(stderr_chunks: list[bytes]) -> str:
    return b"".join(stderr_chunks).decode("utf-8", errors="replace")


def _invalid_framed_output_result(
    *,
    parse_error: ValueError,
    stderr_chunks: list[bytes],
    returncode: int | None,
) -> SmokeResult:
    return SmokeResult(
        ok=False,
        summary=f"{_INVALID_FRAMED_OUTPUT_SUMMARY}{parse_error}",
        stderr=_stderr_text(stderr_chunks),
        returncode=returncode,
    )


def _success_result(
    *,
    responses: tuple[dict[str, Any], ...],
    stderr_chunks: list[bytes],
    returncode: int | None,
) -> SmokeResult:
    return SmokeResult(
        ok=True,
        summary=_SUCCESS_SUMMARY,
        responses=responses,
        stderr=_stderr_text(stderr_chunks),
        returncode=returncode,
    )


def _handshake_exit_result(
    *,
    responses: tuple[dict[str, Any], ...],
    stderr_text: str,
    returncode: int | None,
) -> SmokeResult:
    return SmokeResult(
        ok=False,
        summary=f"{_HANDSHAKE_EXITED_SUMMARY}with code {returncode}.",
        responses=responses,
        stderr=stderr_text,
        returncode=returncode,
    )


def _complete_handshake_result(
    *,
    process: subprocess.Popen[bytes],
    responses_list: list[dict[str, Any]],
    stderr_chunks: list[bytes],
    stderr_thread: threading.Thread,
) -> SmokeResult:
    if process.poll() is None:
        _stop_process(process)
        returncode = 0
    else:
        returncode = process.returncode
    stderr_thread.join(timeout=1.0)
    responses = tuple(responses_list)
    if returncode not in (0, None):
        return _handshake_exit_result(
            responses=responses,
            stderr_text=_stderr_text(stderr_chunks),
            returncode=returncode,
        )
    return _success_result(
        responses=responses,
        stderr_chunks=stderr_chunks,
        returncode=0,
    )


def _completed_process_result(
    *,
    process: subprocess.Popen[bytes],
    responses: tuple[dict[str, Any], ...],
    stderr_chunks: list[bytes],
) -> SmokeResult:
    stderr_text = _stderr_text(stderr_chunks)
    initialize_response = _find_response(responses, _INITIALIZE_REQUEST_ID)
    tools_list_response = _find_response(responses, _TOOLS_LIST_REQUEST_ID)
    if initialize_response is None:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP smoke did not receive an initialize response.",
            responses=responses,
            stderr=stderr_text,
            returncode=process.returncode,
        )
    if tools_list_response is None:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP smoke did not receive a tools/list response.",
            responses=responses,
            stderr=stderr_text,
            returncode=process.returncode,
        )
    if "result" not in initialize_response:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP initialize response did not contain a result payload.",
            responses=responses,
            stderr=stderr_text,
            returncode=process.returncode,
        )
    if "result" not in tools_list_response:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP tools/list response did not contain a result payload.",
            responses=responses,
            stderr=stderr_text,
            returncode=process.returncode,
        )
    tools_payload = tools_list_response["result"]
    if not isinstance(tools_payload, dict) or "tools" not in tools_payload:
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP tools/list response did not expose a tools array.",
            responses=responses,
            stderr=stderr_text,
            returncode=process.returncode,
        )
    if process.returncode != 0:
        return _handshake_exit_result(
            responses=responses,
            stderr_text=stderr_text,
            returncode=process.returncode,
        )
    return _success_result(
        responses=responses,
        stderr_chunks=stderr_chunks,
        returncode=process.returncode,
    )


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
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    response_queue: Queue[dict[str, Any] | ValueError] = Queue()
    stderr_chunks: list[bytes] = []
    stdout_thread = threading.Thread(
        target=_read_frames_until_eof,
        args=(process.stdout, response_queue),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_stderr_until_eof,
        args=(process.stderr, stderr_chunks),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    process.stdin.write(_build_handshake())
    process.stdin.close()

    responses_list: list[dict[str, Any]] = []
    parse_error: ValueError | None = None
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        parse_error = _drain_response_queue(response_queue, responses_list)
        if parse_error is not None:
            _stop_process(process)
            stderr_thread.join(timeout=1.0)
            return _invalid_framed_output_result(
                parse_error=parse_error,
                stderr_chunks=stderr_chunks,
                returncode=process.returncode,
            )
        if _has_complete_handshake(responses_list):
            return _complete_handshake_result(
                process=process,
                responses_list=responses_list,
                stderr_chunks=stderr_chunks,
                stderr_thread=stderr_thread,
            )
        if process.poll() is not None:
            break
        time.sleep(0.01)

    stdout_thread.join(timeout=1.0)
    stderr_thread.join(timeout=1.0)
    parse_error = _drain_response_queue(response_queue, responses_list)
    if parse_error is not None:
        return _invalid_framed_output_result(
            parse_error=parse_error,
            stderr_chunks=stderr_chunks,
            returncode=process.returncode,
        )

    responses = tuple(responses_list)
    if process.poll() is None:
        _stop_process(process)
        stderr_thread.join(timeout=1.0)
        if _has_complete_handshake(responses):
            return _success_result(
                responses=responses,
                stderr_chunks=stderr_chunks,
                returncode=0,
            )
        return SmokeResult(
            ok=False,
            summary="neo4j-memory MCP smoke timed out before initialize/tools/list completed.",
            responses=responses,
            stderr=_stderr_text(stderr_chunks),
            returncode=process.returncode,
        )

    return _completed_process_result(
        process=process,
        responses=responses,
        stderr_chunks=stderr_chunks,
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
