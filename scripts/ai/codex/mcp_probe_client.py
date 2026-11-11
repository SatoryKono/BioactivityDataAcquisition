"""Bounded, single-attempt MCP diagnostic clients; payloads remain private."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import json
import os
import time
import urllib.error
import urllib.request

from scripts.ai.codex.native_mcp_config import NativeConfigClient, NativeConfigError

MAX_RESPONSE_BYTES = 1024 * 1024


class ProbeError(RuntimeError):
    """A sanitized failure category; never retain a server error message."""

    def __init__(self, category: str, *, uncertain: bool = False) -> None:
        super().__init__(category)
        self.category = category
        self.uncertain = uncertain


def rpc_result(value: dict) -> dict:
    error = value.get("error")
    if isinstance(error, dict):
        data = error.get("data")
        reason = data.get("reason") if isinstance(data, dict) else None
        if reason == "WORKSPACE_POLICY_DENIED":
            raise ProbeError("WORKSPACE_POLICY_DENIED")
        raise ProbeError("RPC_ERROR")
    result = value.get("result")
    if not isinstance(result, dict):
        raise ProbeError("INVALID_RESPONSE")
    return result


class StdioProbeClient(NativeConfigClient):
    """Reuse the bounded JSONL reader and own-process-only cleanup."""

    def __init__(self, entry: Mapping, workspace: Path, environment: Mapping[str, str]):
        super().__init__(
            [str(entry["command"]), *entry.get("args", [])],
            workspace,
            max_message_bytes=MAX_RESPONSE_BYTES,
            environment=environment,
        )
        self._memory_policy_wrapper = any(
            Path(arg.replace("\\", "/")).name
            in {"mcp_memory_wrapper.ps1", "mcp_memory_wrapper.sh"}
            for arg in entry.get("args", [])
            if isinstance(arg, str)
        )
        self._identifier = 0
        self.transport_seen = False

    def _result(self, value: dict) -> dict:
        self.transport_seen = True
        return rpc_result(value)

    def request(self, method: str, params: dict, timeout: float) -> dict:
        self._identifier += 1
        self.timeout = timeout
        try:
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": self._identifier,
                    "method": method,
                    "params": params,
                }
            )
            return self._response(self._identifier)
        except NativeConfigError as exc:
            if (
                self._memory_policy_wrapper
                and self._process is not None
                and self._process.poll() == 78
            ):
                raise ProbeError("ADAPTER_DISABLED_BY_POLICY") from None
            # NativeConfigError is already sanitized. Do not propagate arbitrary
            # transport/server exceptions or stderr into the report.
            category = (
                "TIMEOUT" if "observation timeout" in str(exc) else "TRANSPORT_ERROR"
            )
            raise ProbeError(category, uncertain=True) from None

    def notify_initialized(self) -> None:
        try:
            self._send(
                {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
            )
        except NativeConfigError:
            raise ProbeError("TRANSPORT_ERROR", uncertain=True) from None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def _http_message(raw: bytes) -> dict:
    text = raw.decode("utf-8")
    if text.lstrip().startswith("{"):
        value = json.loads(text)
    else:
        value = json.loads(
            "\n".join(
                line[5:].strip()
                for line in text.splitlines()
                if line.startswith("data:")
            )
        )
    if not isinstance(value, dict):
        raise ProbeError("INVALID_RESPONSE")
    return value


def _read_http_reply(response, timeout: float) -> bytes:
    if "text/event-stream" not in response.headers.get("Content-Type", ""):
        return response.read(MAX_RESPONSE_BYTES + 1)
    deadline = time.monotonic() + timeout
    event = bytearray()
    for _ in range(1024):
        if time.monotonic() >= deadline:
            raise ProbeError("TIMEOUT", uncertain=True)
        line = response.readline(MAX_RESPONSE_BYTES + 1 - len(event))
        event.extend(line)
        if len(event) > MAX_RESPONSE_BYTES:
            raise ProbeError("RESPONSE_LIMIT", uncertain=True)
        if not line or line.strip() == b"":
            if b"data:" in event and "id" in _http_message(bytes(event)):
                return bytes(event)
            event.clear()
    raise ProbeError("SSE_EVENT_LIMIT", uncertain=True)


class HttpProbeClient:
    """Streamable HTTP with bounded responses and no redirect/replay."""

    def __init__(self, entry: Mapping, workspace: Path, environment: Mapping[str, str]):
        del workspace
        self.url = str(entry["url"])
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        self.headers.update(entry.get("http_headers") or {})
        for key, reference in (entry.get("env_http_headers") or {}).items():
            if not environment.get(reference):
                raise ProbeError("AUTH_REFERENCE_UNAVAILABLE")
            self.headers[key] = environment[reference]
        reference = entry.get("bearer_token_env_var")
        if reference:
            if not environment.get(reference):
                raise ProbeError("AUTH_REFERENCE_UNAVAILABLE")
            self.headers["Authorization"] = "Bearer " + environment[reference]
        if entry.get("http_headers_helper"):
            raise ProbeError("AUTH_HELPER_NOT_TESTED")
        self._opener = urllib.request.build_opener(_NoRedirect())
        self._identifier = 0
        self._last_timeout = 0.0
        self.transport_seen = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        # Never DELETE a shared session or restart its owner.
        self._opener.close()

    def _post(
        self, payload: dict, timeout: float, *, notification: bool = False
    ) -> dict:
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers=self.headers,
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=timeout) as response:
                session = response.headers.get("Mcp-Session-Id")
                if session:
                    self.headers["Mcp-Session-Id"] = session
                if notification and response.status in (200, 202, 204):
                    return {}
                raw = _read_http_reply(response, timeout)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ProbeError("RESPONSE_LIMIT", uncertain=True)
            return _http_message(raw)
        except urllib.error.HTTPError as exc:
            category = "AUTH_ERROR" if exc.code in (401, 403) else "HTTP_ERROR"
            raise ProbeError(category) from None
        except (TimeoutError, OSError):
            raise ProbeError("TIMEOUT_OR_CONNECTION", uncertain=True) from None
        except (ValueError, UnicodeError):
            raise ProbeError("INVALID_RESPONSE", uncertain=True) from None

    def request(self, method: str, params: dict, timeout: float) -> dict:
        self._identifier += 1
        self._last_timeout = timeout
        value = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._identifier,
                "method": method,
                "params": params,
            },
            timeout,
        )
        self.transport_seen = True
        if value.get("id") != self._identifier:
            raise ProbeError("RESPONSE_ID_MISMATCH", uncertain=True)
        result = rpc_result(value)
        if method == "initialize" and isinstance(result.get("protocolVersion"), str):
            self.headers["MCP-Protocol-Version"] = result["protocolVersion"]
        return result

    def notify_initialized(self):
        self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            self._last_timeout,
            notification=True,
        )


def probe_environment(
    entry: Mapping, repository_env: Mapping[str, str]
) -> dict[str, str]:
    """Pass ordinary process infrastructure plus explicitly configured variables."""
    infrastructure = {
        "PATH",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "TEMP",
        "TMP",
        "PROGRAMFILES",
        "PROGRAMDATA",
        "LANG",
    }
    result = {
        key: value for key, value in os.environ.items() if key.upper() in infrastructure
    }
    result.update(entry.get("env") or {})
    references = set(entry.get("env_vars") or []) | set(
        (entry.get("env_http_headers") or {}).values()
    )
    if entry.get("bearer_token_env_var"):
        references.add(entry["bearer_token_env_var"])
    for key in references:
        if key in repository_env:
            result[key] = repository_env[key]
    return result


def _approved_stdio_shape(entry: Mapping, workspace: Path) -> None:
    launcher = Path(str(entry.get("command", ""))).stem.lower()
    prefixes = {
        "python": {"-I", "-S", "-B", "-u"},
        "python3": {"-I", "-S", "-B", "-u"},
        "node": {"--no-warnings"},
        "pwsh": {"-NoProfile", "-NonInteractive", "-File"},
        "powershell": {"-NoProfile", "-NonInteractive", "-File"},
        "bash": {"--noprofile", "--norc"},
    }
    if launcher not in prefixes:
        raise ProbeError("INSTALL_OR_UNREVIEWED_LAUNCHER_NOT_TESTED")
    args = entry.get("args", [])
    if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        raise ProbeError("ADAPTER_ARGUMENTS_INVALID")
    for arg in args:
        if arg in prefixes[launcher]:
            continue
        path = Path(arg)
        actual = path if path.is_absolute() else workspace / path
        if (
            path.suffix.lower() in {".py", ".js", ".mjs", ".ps1", ".sh"}
            and actual.is_file()
        ):
            return
        raise ProbeError("ADAPTER_PREFIX_NOT_TESTED")
    raise ProbeError("EXISTING_ADAPTER_REQUIRED")


def client_for(entry: Mapping, workspace: Path, environment: Mapping[str, str]):
    if entry.get("command"):
        _approved_stdio_shape(entry, workspace)
        return StdioProbeClient(entry, workspace, environment)
    if entry.get("url"):
        return HttpProbeClient(entry, workspace, environment)
    raise ProbeError("UNSUPPORTED_TRANSPORT")
