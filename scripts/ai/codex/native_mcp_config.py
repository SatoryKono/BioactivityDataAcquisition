"""Bounded native Codex config/read capture without starting an MCP session.

Configuration resolution stays owned by Codex. This client creates only its own
diagnostic app-server process: it never starts a thread, model turn, or MCP tool.
Raw configuration is private in memory and must be projected before logging.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from typing import Any

_MAX_MESSAGE_BYTES = 8 * 1024 * 1024
_MAX_MESSAGES = 1024


class NativeConfigError(RuntimeError):
    """A bounded native operation failed; raw stderr/config is never included."""


@dataclass(frozen=True)
class ConfigCapture:
    """Private native result plus the physical workspace it was resolved for."""

    workspace: Path
    payload: Mapping[str, Any] = field(repr=False)
    native_version: str | None = None
    authority: str = "native Codex config/read; diagnostic process"

    def revisions(self) -> tuple[str, ...]:
        """Return private revision tokens for in-memory drift checks only."""
        return tuple(
            str(layer.get("version", ""))
            for layer in self.payload.get("layers", []) or []
        )


class NativeConfigClient:
    """Own one short-lived JSONL process and refuse interactive requests."""

    def __init__(
        self,
        command: Sequence[str],
        workspace: Path,
        *,
        timeout: float = 30.0,
        max_message_bytes: int = _MAX_MESSAGE_BYTES,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if (
            not command
            or timeout <= 0
            or not 1024 <= max_message_bytes <= _MAX_MESSAGE_BYTES
        ):
            raise ValueError("invalid native config diagnostic bounds")
        self.command = tuple(command)
        self._environment = dict(environment) if environment is not None else None
        self.workspace = workspace.resolve(strict=True)
        self.timeout = timeout
        self.max_message_bytes = max_message_bytes
        self._messages: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=32)
        self._failed = threading.Event()
        self._stop_reading = threading.Event()
        self._reader: threading.Thread | None = None
        self._process: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> NativeConfigClient:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self._process = subprocess.Popen(
                self.command,
                cwd=self.workspace,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                env=self._environment,
            )
        except OSError:
            raise NativeConfigError("native config process could not start") from None
        try:
            os.set_blocking(self._process.stdout.fileno(), False)
        except (OSError, AttributeError):
            NativeConfigClient.__exit__(self, None, None, None)
            raise NativeConfigError(
                "native config nonblocking pipe unavailable"
            ) from None
        self._reader = threading.Thread(target=self._read_messages, daemon=True)
        self._reader.start()
        return self

    def _put(self, message: dict[str, Any] | None) -> None:
        try:
            self._messages.put(message, timeout=0.1)
        except queue.Full:
            self._failed.set()

    def _read_available(self, size: int) -> bytes | None:
        process = self._process
        if process is None or process.stdout is None:
            raise ValueError("native config output unavailable")
        try:
            return os.read(process.stdout.fileno(), size)
        except BlockingIOError:
            self._stop_reading.wait(0.005)
            return None

    def _lines(self):
        pending = bytearray()
        while not self._stop_reading.is_set():
            chunk = self._read_available(
                min(65536, self.max_message_bytes + 1 - len(pending))
            )
            if chunk is None:
                continue
            if not chunk:
                if pending:
                    yield bytes(pending)
                return
            pending.extend(chunk)
            while b"\n" in pending:
                end = pending.index(b"\n") + 1
                yield bytes(pending[:end])
                del pending[:end]
            if len(pending) > self.max_message_bytes:
                raise ValueError("native config message exceeded bounds")

    def _read_messages(self) -> None:
        try:
            for count, line in enumerate(self._lines()):
                if self._stop_reading.is_set():
                    break
                if count >= _MAX_MESSAGES or len(line) > self.max_message_bytes:
                    raise ValueError("native config output exceeded bounds")
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("native config response is not an object")
                self._put(value)
        except (OSError, ValueError):
            self._failed.set()
        finally:
            self._put(None)

    def _stop_reader(self) -> bool:
        self._stop_reading.set()
        if self._reader is None:
            return True
        self._reader.join(timeout=0.5)
        return not self._reader.is_alive()

    def _send(self, value: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None:
            raise NativeConfigError("native config process is not open")
        try:
            process.stdin.write(json.dumps(value).encode("utf-8") + b"\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError):
            raise NativeConfigError("native config connection closed") from None

    @staticmethod
    def _result(value: dict[str, Any]) -> dict[str, Any]:
        if "error" in value:
            raise NativeConfigError("native config request was rejected")
        result = value.get("result")
        if not isinstance(result, dict):
            raise NativeConfigError("native config result is not an object")
        return result

    def _response(self, identifier: int) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self._failed.is_set():
                raise NativeConfigError(
                    "native config response exceeded bounds or was malformed"
                )
            try:
                value = self._messages.get(
                    timeout=min(0.1, max(0.001, deadline - time.monotonic()))
                )
            except queue.Empty:
                continue
            if value is None:
                detail = (
                    "native config response exceeded bounds or was malformed"
                    if self._failed.is_set()
                    else "native config process closed before responding"
                )
                raise NativeConfigError(detail)
            if "method" in value and "id" in value:
                raise NativeConfigError(
                    "interactive native request refused; no approval supplied"
                )
            if value.get("id") == identifier:
                return self._result(value)
        raise NativeConfigError(
            "native config observation timeout; no restart or replay"
        )

    def read(self) -> ConfigCapture:
        """Read effective config and origins with the same native resolver as Codex."""
        self._send(
            {
                "id": 0,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "bioetl_mcp_config", "version": "1"},
                    "capabilities": {"experimentalApi": True},
                },
            }
        )
        initialized = self._response(0)
        self._send({"method": "initialized", "params": {}})
        self._send(
            {
                "id": 1,
                "method": "config/read",
                "params": {"cwd": str(self.workspace), "includeLayers": True},
            }
        )
        payload = self._response(1)
        if not isinstance(payload.get("config"), dict) or not isinstance(
            payload.get("origins"), dict
        ):
            raise NativeConfigError("native config/origins contract unavailable")
        user_agent = initialized.get("userAgent", "")
        version = (
            re.search(r"\b\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?\b", user_agent)
            if isinstance(user_agent, str) and "codex" in user_agent.lower()
            else None
        )
        return ConfigCapture(
            self.workspace,
            payload,
            native_version=version.group(0) if version else None,
        )

    def __exit__(self, *_: object) -> None:
        process = self._process
        if process is None:
            return
        reader_stopped = self._stop_reader()
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        finally:
            if process.stdout is not None:
                # The reader uses nonblocking os.read, not BufferedReader's lock.
                # Closing this end never waits for an inherited writer to exit.
                process.stdout.close()
        if not reader_stopped:
            raise NativeConfigError("native config reader cleanup not verified")
