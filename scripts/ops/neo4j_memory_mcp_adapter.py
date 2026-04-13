#!/usr/bin/env python3
"""Bridge framed MCP stdio to the line-delimited stdio used by the upstream Neo4j memory server."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from queue import Queue
from typing import Any, BinaryIO


@dataclass(slots=True)
class PumpError:
    source: str
    message: str


def _read_exactly(stream: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError("Unexpected EOF while reading framed MCP payload.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_framed_message(stream: BinaryIO) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    saw_header = False
    while True:
        line = stream.readline()
        if not line:
            return None if not saw_header else None
        saw_header = True
        if line == b"\r\n":
            break
        name, sep, value = line.decode("ascii").partition(":")
        if not sep:
            raise ValueError(f"Malformed framed MCP header line: {line!r}")
        headers[name.strip().lower()] = value.strip()
    content_length_raw = headers.get("content-length")
    if content_length_raw is None:
        raise ValueError("Framed MCP message missing Content-Length header.")
    body = _read_exactly(stream, int(content_length_raw))
    return json.loads(body.decode("utf-8"))


def _write_framed_message(stream: BinaryIO, message: dict[str, Any]) -> None:
    body = json.dumps(message, separators=(",", ":"), sort_keys=True).encode("utf-8")
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    stream.write(body)
    stream.flush()


def _read_line_message(stream: BinaryIO) -> dict[str, Any] | None:
    line = stream.readline()
    if not line:
        return None
    return json.loads(line.decode("utf-8"))


def _write_line_message(stream: BinaryIO, message: dict[str, Any]) -> None:
    stream.write(json.dumps(message, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    stream.write(b"\n")
    stream.flush()


def _pump_framed_to_line(
    *,
    source: BinaryIO,
    target: BinaryIO,
    errors: Queue[PumpError],
) -> None:
    try:
        while True:
            message = _read_framed_message(source)
            if message is None:
                break
            _write_line_message(target, message)
    except Exception as exc:  # pragma: no cover - exercised via subprocess tests
        errors.put(PumpError("client->server", str(exc)))
    finally:
        try:
            target.close()
        except BrokenPipeError:
            pass


def _pump_line_to_framed(
    *,
    source: BinaryIO,
    target: BinaryIO,
    errors: Queue[PumpError],
) -> None:
    try:
        while True:
            message = _read_line_message(source)
            if message is None:
                break
            _write_framed_message(target, message)
    except Exception as exc:  # pragma: no cover - exercised via subprocess tests
        errors.put(PumpError("server->client", str(exc)))


def _pump_stderr(source: BinaryIO, target: BinaryIO) -> None:
    for chunk in iter(lambda: source.readline(), b""):
        target.write(chunk)
        target.flush()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Inner server command, introduced by --.",
    )
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("Missing inner server command. Pass it after --.")
    args.command = command
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    process = subprocess.Popen(
        list(args.command),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    errors: Queue[PumpError] = Queue()
    threads = [
        threading.Thread(
            target=_pump_framed_to_line,
            kwargs={
                "source": sys.stdin.buffer,
                "target": process.stdin,
                "errors": errors,
            },
            daemon=True,
        ),
        threading.Thread(
            target=_pump_line_to_framed,
            kwargs={
                "source": process.stdout,
                "target": sys.stdout.buffer,
                "errors": errors,
            },
            daemon=True,
        ),
        threading.Thread(
            target=_pump_stderr,
            kwargs={"source": process.stderr, "target": sys.stderr.buffer},
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    returncode = process.wait()
    for thread in threads:
        thread.join(timeout=1.0)

    if not errors.empty():
        error = errors.get()
        print(
            f"neo4j-memory MCP adapter error on {error.source}: {error.message}",
            file=sys.stderr,
        )
        return 1
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
