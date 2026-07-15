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
import subprocess
import threading
import time
import tomllib
from pathlib import Path
from typing import Any, TextIO


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
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        servers = config.get("mcp_servers", {})
    else:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        servers = config.get("mcpServers", config.get("servers", {}))
    server = servers[server_name]
    if not isinstance(server, dict):
        raise ValueError(f"Invalid MCP server definition: {server_name}")
    if "command" not in server:
        raise ValueError(
            "Protocol smoke currently requires a stdio server command; "
            "HTTP/OAuth servers are validated by their frontend transport"
        )
    return server


def smoke_server(
    config_path: Path,
    server_name: str,
    *,
    timeout: float = 15.0,
) -> dict[str, Any]:
    server = _load_server(config_path, server_name)
    command = [str(server["command"]), *map(str, server.get("args", []))]
    environment = os.environ.copy()
    environment.update({str(k): str(v) for k, v in server.get("env", {}).items()})
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=config_path.parent,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
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
            raise RuntimeError("MCP initialize failed")
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
            raise RuntimeError("MCP tools/list failed")
        return {
            "schema_version": "bioetl-mcp-protocol-smoke-v1",
            "server": server_name,
            "ok": True,
            "tool_count": len(tool_rows),
            "duration_ms": round((time.monotonic() - started) * 1000),
            "command": command,
            "environment_names": sorted(server.get("env", {})),
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


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
