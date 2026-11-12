"""Bounded, single-attempt MCP diagnostic clients; payloads remain private."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import os
import json
import time

from scripts.ai.codex.native_mcp_config import NativeConfigClient, NativeConfigError

from scripts.ai.codex.mcp_probe_errors import (
    ProbeError as ProbeError,
    rpc_result as rpc_result,
)
from scripts.ai.codex.mcp_http_probe import (
    MAX_RESPONSE_BYTES,
    HttpProbeClient,
    _read_http_reply as _read_http_reply,
)


class StdioProbeClient(NativeConfigClient):
    """Reuse the bounded JSONL reader and own-process-only cleanup."""

    def __init__(self, entry: Mapping, workspace: Path, environment: Mapping[str, str]):
        super().__init__(
            [str(entry["command"]), *entry.get("args", [])],
            _execution_directory(entry, workspace),
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
        self._deadline = 0.0
        self._timed_out = False

    def __enter__(self):
        super().__enter__()
        try:
            os.set_blocking(self._process.stdin.fileno(), False)
        except (OSError, AttributeError):
            super().__exit__(None, None, None)
            raise ProbeError("NONBLOCKING_STDIO_NOT_SUPPORTED") from None
        return self

    def __exit__(self, *args):
        # Do not spend the normal grace period on an unresponsive adapter.
        # Only this Popen process is terminated, never a shared owner.
        if (
            self._timed_out
            and self._process is not None
            and self._process.poll() is None
        ):
            self._process.terminate()
        super().__exit__(*args)

    def _remaining(self) -> float:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            self._timed_out = True
            raise ProbeError("TIMEOUT", uncertain=True)
        return remaining

    def _send(self, value: dict) -> None:
        if self._process is None or self._process.stdin is None:
            raise NativeConfigError("native MCP request process unavailable")
        encoded = json.dumps(value).encode() + b"\n"
        if len(encoded) > MAX_RESPONSE_BYTES:
            raise ProbeError("REQUEST_LIMIT")
        remaining = memoryview(encoded)
        while remaining:
            budget = self._remaining()
            try:
                written = os.write(self._process.stdin.fileno(), remaining)
            except BlockingIOError:
                time.sleep(min(0.005, budget))
                continue
            except OSError:
                raise NativeConfigError("native MCP request send failed") from None
            if written <= 0:
                raise NativeConfigError("native MCP request send failed")
            remaining = remaining[written:]

    def _result(self, value: dict) -> dict:
        self.transport_seen = True
        return rpc_result(value)

    def request(self, method: str, params: dict, timeout: float) -> dict:
        self._identifier += 1
        self._deadline = time.monotonic() + timeout
        try:
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": self._identifier,
                    "method": method,
                    "params": params,
                }
            )
            self.timeout = self._remaining()
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
            self._timed_out = category == "TIMEOUT"
            raise ProbeError(category, uncertain=True) from None

    def notify_initialized(self) -> None:
        try:
            self._send(
                {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
            )
        except NativeConfigError:
            raise ProbeError("TRANSPORT_ERROR", uncertain=True) from None


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
    result.update(_declared_environment(entry, repository_env))
    # An explicit task restriction must survive the wrapper's dotenv loading.
    # Preserve only this non-secret policy variable, not unrelated credentials.
    if "BIOETL_AI_MEMORY_MODE" in os.environ:
        result["BIOETL_AI_MEMORY_MODE"] = os.environ["BIOETL_AI_MEMORY_MODE"]
    return result


def _declared_environment(
    entry: Mapping, repository_env: Mapping[str, str]
) -> dict[str, str]:
    result = {}
    references = set(entry.get("env_vars") or []) | set(
        (entry.get("env_http_headers") or {}).values()
    )
    if entry.get("bearer_token_env_var"):
        references.add(entry["bearer_token_env_var"])
    explicit = entry.get("env") or {}
    for key in references:
        if key in explicit:
            continue
        if key in repository_env:
            result[key] = repository_env[key]
        elif key in os.environ:
            result[key] = os.environ[key]
    return result


def _execution_directory(entry: Mapping, workspace: Path) -> Path:
    """Use the effective native cwd, resolving relative values from workspace."""
    configured = entry.get("cwd")
    if configured is None:
        return workspace.resolve(strict=True)
    if not isinstance(configured, str) or not configured:
        raise ProbeError("ADAPTER_CWD_INVALID")
    directory = Path(configured)
    if not directory.is_absolute():
        directory = workspace / directory
    directory = directory.resolve(strict=True)
    if not directory.is_dir():
        raise ProbeError("ADAPTER_CWD_INVALID")
    return directory


def _require_no_install_adapter(path: Path) -> None:
    # Legacy project wrappers can fall through to npx/uvx package installation.
    # File existence and a host marker cannot prove that fallback is impossible.
    name = path.resolve(strict=True).name.lower()
    if name.startswith("mcp_") and name.endswith(("_wrapper.sh", "_wrapper.ps1")):
        raise ProbeError("WRAPPER_BACKEND_NO_INSTALL_NOT_VERIFIED")


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
    workspace = _execution_directory(entry, workspace)
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
            _require_no_install_adapter(actual)
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
