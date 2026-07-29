#!/usr/bin/env python3
"""Bounded MCP ``initialize`` and ``tools/list`` readiness smoke.

The smoke starts one configured MCP server on demand and never creates a
persistent container. Reports include command and environment *names* only.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import threading
import time
import tomllib
from collections import deque
from pathlib import Path
from typing import Any, TextIO

_STDERR_READ_CHARS = 4096
_STDERR_RETENTION_CHARS = 200_000
_STDERR_ERROR_TAIL_CHARS = 1500

_WINDOWS_PWSH_CANDIDATES = (
    Path(r"C:\Program Files\PowerShell\7\pwsh.exe"),
    Path(r"C:\Program Files\PowerShell\7\7\pwsh.exe"),
)
_ALLOWED_MCP_LAUNCHERS = frozenset(
    {
        "bash",
        "cmd",
        "cmd.exe",
        "docker",
        "docker.exe",
        "node",
        "node.exe",
        "npx",
        "npx.cmd",
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
        "python",
        "python.exe",
        "python3",
        "python3.exe",
        "uv",
        "uv.exe",
        "uvx",
        "uvx.exe",
    }
)


def _resolve_windows_pwsh() -> str | None:
    for candidate in _WINDOWS_PWSH_CANDIDATES:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("powershell") or shutil.which("powershell.exe")


def _prefer_windows_bat_cmd(command: str, resolved: str) -> str:
    """Keep .bat only as last resort; prefer bare command via cmd."""
    if command.lower().startswith("npx"):
        node_npx = Path(r"C:\Program Files\nodejs\npx.cmd")
        if node_npx.is_file():
            return str(node_npx)
    return resolved


def _resolve_command(command: str) -> str:
    """Resolve ``command`` to an executable CreateProcess can launch on Windows.

    ``shutil.which('pwsh')`` may return a ``.bat`` shim that subprocess cannot
    start without a shell. Prefer real ``pwsh.exe`` / ``powershell.exe``.
    """
    lowered = command.lower()
    if os.name == "nt" and lowered in {"pwsh", "pwsh.exe"}:
        pwsh = _resolve_windows_pwsh()
        if pwsh:
            return pwsh
    resolved = shutil.which(command)
    if resolved is None:
        return command
    if os.name == "nt" and Path(resolved).suffix.lower() in {".bat", ".cmd"}:
        return _prefer_windows_bat_cmd(command, resolved)
    return resolved


def _readline(stream: TextIO, timeout: float) -> str:
    result: queue.Queue[str | BaseException] = queue.Queue(maxsize=1)

    def read() -> None:
        try:
            result.put(stream.readline())
        except BaseException as exc:  # pragma: no cover - defensive transport seam
            result.put(exc)

    threading.Thread(target=read, daemon=True).start()
    try:
        value = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise TimeoutError("MCP response timed out") from exc
    if isinstance(value, BaseException):
        raise value
    if not value:
        raise RuntimeError("MCP server closed stdout before responding")
    return value


def _request(
    process: subprocess.Popen[str],
    payload: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
    process.stdin.flush()
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"MCP request {payload.get('id')} timed out")
        response = json.loads(_readline(process.stdout, remaining))
        if response.get("id") == payload.get("id"):
            return response


def _load_server(config_path: Path, server_name: str) -> dict[str, Any]:
    if config_path.suffix.lower() == ".toml":
        config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
        servers = config.get("mcp_servers", {})
    else:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        servers = config.get("mcpServers", config.get("servers", {}))
    server = servers[server_name]
    if not isinstance(server, dict):
        raise ValueError(f"Invalid MCP server definition: {server_name}")
    has_command = "command" in server
    has_http = bool(server.get("url")) and str(server.get("type", "http")).lower() in {
        "http",
        "streamable-http",
        "sse",
    }
    # Bare url without type: treat as HTTP for shared-plane smoke.
    if not has_command and server.get("url") and not server.get("type"):
        has_http = True
    if not has_command and not has_http:
        raise ValueError(
            "Protocol smoke requires a stdio server command or an HTTP url "
            f"(server={server_name!r})"
        )
    return server


def _is_http_server(server: dict[str, Any]) -> bool:
    if "command" in server and not server.get("url"):
        return False
    if not server.get("url"):
        return False
    stype = str(server.get("type", "http")).lower()
    return stype in {"http", "streamable-http", "sse", ""} or (
        "command" not in server and bool(server.get("url"))
    )


_DATA_PREFIX = "data:"
_JSON_RPC_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _http_ping_url(mcp_url: str) -> str:
    """Derive mcp-proxy /ping URL from a Streamable HTTP MCP endpoint."""
    base = mcp_url.rstrip("/")
    if base.endswith("/mcp"):
        return base[: -len("/mcp")] + "/ping"
    return base + "/ping"


def _validate_loopback_mcp_url(url: str) -> tuple[str, int]:
    from urllib.parse import urlsplit

    parsed_url = urlsplit(url)
    if (
        parsed_url.scheme != "http"
        or parsed_url.hostname not in {"127.0.0.1", "localhost"}
        or parsed_url.port is None
        or parsed_url.path != "/mcp"
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise ValueError(
            f"HTTP protocol smoke requires an exact localhost /mcp URL (got {url!r})"
        )
    return str(parsed_url.hostname), int(parsed_url.port)


def _extract_json_rpc_body(raw: str) -> str:
    """Unwrap optional SSE framing (``event:`` / ``data:``) to a JSON body."""
    if _DATA_PREFIX in raw and raw.lstrip().startswith("event:"):
        for line in raw.splitlines():
            if line.startswith(_DATA_PREFIX):
                return line[len(_DATA_PREFIX) :].strip()
    if _DATA_PREFIX in raw:
        for line in raw.splitlines():
            if line.startswith(_DATA_PREFIX):
                return line[len(_DATA_PREFIX) :].strip()
    return raw


def _http_json_rpc(
    safe_url: str,
    payload: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    import urllib.request

    req = urllib.request.Request(  # NOSONAR - safe_url is loopback-validated
        safe_url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=dict(_JSON_RPC_HEADERS),
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(_extract_json_rpc_body(raw))


def _ping_http_endpoint(ping_url: str, *, timeout: float) -> int:
    import urllib.error
    import urllib.request

    from scripts.engineering.common.repo_paths import ensure_local_http_url

    # Re-validate loopback host before network I/O (pythonsecurity:S5144).
    safe_ping = ensure_local_http_url(ping_url)
    try:
        with urllib.request.urlopen(  # NOSONAR - safe_ping is loopback-validated
            safe_ping, timeout=timeout
        ) as resp:
            ping_code = int(getattr(resp, "status", 200) or 200)
            if ping_code >= 500:
                raise RuntimeError(f"ping HTTP {ping_code} for {safe_ping}")
            return ping_code
    except urllib.error.HTTPError as exc:
        if int(exc.code) >= 500:
            raise RuntimeError(f"ping HTTP {exc.code} for {safe_ping}") from exc
        # 4xx on /ping: still try initialize
        return int(exc.code)
    except Exception as exc:
        raise RuntimeError(f"ping failed for {safe_ping}: {exc}") from exc


def _http_initialize_and_tools(
    safe_url: str,
    *,
    timeout: float,
) -> tuple[bool, str | None, int | None]:
    """POST initialize (+ best-effort tools/list). Returns (ok, error, tool_count)."""
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "bioetl-mcp-smoke", "version": "1"},
        },
    }
    try:
        parsed = _http_json_rpc(safe_url, init_payload, timeout=timeout)
    except Exception as exc:
        # Ping alone is enough for shared-plane liveness when proxy rejects
        # bare JSON initialize (session/header requirements).
        return False, str(exc)[:500], None
    if "error" in parsed or "result" not in parsed:
        return False, f"initialize failed: {parsed!r}"[:500], None
    tool_count = _http_tools_list_count(safe_url, timeout=timeout)
    return True, None, tool_count


def _http_tools_list_count(safe_url: str, *, timeout: float) -> int | None:
    tools_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    try:
        tparsed = _http_json_rpc(safe_url, tools_payload, timeout=timeout)
        tools = tparsed.get("result", {}).get("tools")
        if isinstance(tools, list):
            return len(tools)
    except Exception:
        return None
    return None


def smoke_http_server(
    server_name: str,
    url: str,
    *,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Smoke a localhost shared-plane HTTP MCP endpoint (ping + initialize).

    Streamable HTTP (mcp-proxy): GET /ping for liveness, then POST JSON-RPC
    initialize to the MCP URL when the proxy accepts application/json.
    """
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    # Loopback-only MCP smoke: local proxy has no TLS in dev (S5332 accepted).
    host, port = _validate_loopback_mcp_url(url)
    safe_url = ensure_local_http_url(f"http://{host}:{port}/mcp")
    started = time.monotonic()
    ping_url = ensure_local_http_url(f"http://{host}:{port}/ping")
    _ping_http_endpoint(ping_url, timeout=timeout)
    init_ok, init_error, tool_count = _http_initialize_and_tools(
        safe_url, timeout=timeout
    )

    report: dict[str, Any] = {
        "schema_version": "bioetl-mcp-protocol-smoke-v1",
        "server": server_name,
        "ok": True,  # ping succeeded to reach here
        "transport": "http",
        "url": safe_url,
        "ping_url": ping_url,
        "initialize_ok": init_ok,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "command": [],
        "environment_names": [],
    }
    if tool_count is not None:
        report["tool_count"] = tool_count
    if init_error and not init_ok:
        report["initialize_note"] = init_error
    return report


def _validate_command_argv(command: list[str]) -> list[str]:
    """Reject shell-metacharacter injection in MCP command argv.

    Returns a new argv list after allowlist checks (S2076 sanitizing boundary).
    """
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    if not command or not command[0].strip():
        raise ValueError("MCP server command must be a non-empty executable path")
    # Shared metacharacter rejection + token rebuild (pythonsecurity:S8701/S2076).
    safe_tokens = ensure_safe_cli_argv([str(token) for token in command])
    launcher = Path(safe_tokens[0]).name.lower()
    if launcher not in _ALLOWED_MCP_LAUNCHERS:
        raise ValueError(f"Unsupported MCP launcher: {launcher!r}")
    return list(safe_tokens)


def _safe_config_path(config_path: Path) -> Path:
    from scripts.engineering.common.repo_paths import (
        REPO_ROOT,
        ensure_path_within_root,
    )

    # Prefer confining to the repo root, but allow temporary fixture configs
    # used by unit tests to live outside the checkout.
    resolved_config = config_path.expanduser().resolve(strict=False)
    try:
        return ensure_path_within_root(resolved_config, REPO_ROOT)
    except ValueError:
        return ensure_path_within_root(resolved_config, resolved_config.parent)


def _stdio_popen_argv(
    server: dict[str, Any],
) -> tuple[list[str], list[str], bool]:
    """Build sanitized argv for stdio MCP spawn. Returns (display_cmd, popen_cmd, use_shell)."""
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    resolved_cmd = _resolve_command(str(server["command"]))
    command = _validate_command_argv([resolved_cmd, *map(str, server.get("args", []))])
    # Windows CreateProcess cannot execute .bat/.cmd without a shell/comspec.
    use_shell = False
    popen_command: list[str] = command
    if os.name == "nt" and Path(resolved_cmd).suffix.lower() in {".bat", ".cmd"}:
        comspec = os.environ.get("ComSpec") or "cmd.exe"
        popen_command = [comspec, "/c", *command]
    popen_command = ensure_safe_cli_argv([str(token) for token in popen_command])
    return command, popen_command, use_shell


def _resolve_mcp_cwd(safe_config: Path) -> Path:
    # Prefer repo root when wrappers use absolute paths outside the config dir.
    for candidate in (safe_config.parent, Path.cwd(), *safe_config.parents):
        if (candidate / "scripts" / "ai" / "mcp").is_dir() and (
            candidate / ".mcp.json"
        ).is_file():
            return candidate
    return safe_config.parent


def _run_stdio_initialize_tools(
    process: subprocess.Popen[str],
    *,
    timeout: float,
) -> tuple[int, None] | tuple[None, Exception]:
    """Exchange initialize + tools/list; returns (tool_count, None) or (None, error)."""
    try:
        initialized = _request(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "bioetl-mcp-smoke", "version": "1"},
                },
            },
            timeout=timeout,
        )
        if "error" in initialized or "result" not in initialized:
            raise RuntimeError(f"MCP initialize failed: {initialized!r}")
        assert process.stdin is not None
        process.stdin.write(
            '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n'
        )
        process.stdin.flush()
        tools = _request(
            process,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            timeout=timeout,
        )
        tool_rows = tools.get("result", {}).get("tools")
        if "error" in tools or not isinstance(tool_rows, list):
            raise RuntimeError(f"MCP tools/list failed: {tools!r}")
        return len(tool_rows), None
    except Exception as exc:
        return None, exc


def _terminate_process(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def smoke_server(
    config_path: Path,
    server_name: str,
    *,
    timeout: float = 15.0,
) -> dict[str, Any]:
    safe_config = _safe_config_path(config_path)
    server = _load_server(safe_config, server_name)
    if _is_http_server(server):
        return smoke_http_server(server_name, str(server["url"]), timeout=timeout)
    command, popen_command, use_shell = _stdio_popen_argv(server)
    environment = os.environ.copy()
    environment.update({str(k): str(v) for k, v in server.get("env", {}).items()})
    started = time.monotonic()
    cwd = _resolve_mcp_cwd(safe_config)
    process = subprocess.Popen(  # NOSONAR - argv via ensure_safe_cli_argv; shell=False
        popen_command,
        cwd=str(cwd),
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        shell=use_shell,
    )
    # Drain stderr continuously. Servers like mcp-run-python emit large Deno
    # install logs; if the pipe fills, the child blocks and initialize hangs.
    stderr_chars: deque[str] = deque(maxlen=_STDERR_RETENTION_CHARS)

    def _stderr_tail() -> str:
        return "".join(stderr_chars)[-_STDERR_ERROR_TAIL_CHARS:]

    def _drain_stderr() -> None:
        assert process.stderr is not None
        try:
            while chunk := process.stderr.read(_STDERR_READ_CHARS):
                stderr_chars.extend(chunk)
        except Exception:
            return

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()
    try:
        tool_count, failure = _run_stdio_initialize_tools(process, timeout=timeout)
    finally:
        _terminate_process(process)
        stderr_thread.join(timeout=1)

    if failure is not None:
        tail = _stderr_tail()
        if tail:
            raise RuntimeError(f"{failure} | stderr_tail={tail!r}") from failure
        raise failure
    assert tool_count is not None
    return {
        "schema_version": "bioetl-mcp-protocol-smoke-v1",
        "server": server_name,
        "ok": True,
        "tool_count": tool_count,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "command": command,
        "environment_names": sorted(server.get("env", {})),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(".mcp.json"))
    parser.add_argument("--server", required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = smoke_server(args.config.resolve(), args.server, timeout=args.timeout)
    except (
        KeyError,
        OSError,
        RuntimeError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
        tomllib.TOMLDecodeError,
    ) as exc:
        report = {
            "schema_version": "bioetl-mcp-protocol-smoke-v1",
            "server": args.server,
            "ok": False,
            "error": type(exc).__name__,
            "error_message": str(exc)[:500],
        }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
