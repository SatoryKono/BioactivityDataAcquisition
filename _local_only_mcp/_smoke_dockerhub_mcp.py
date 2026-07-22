"""One-shot Docker Hub MCP smoke: initialize, tools/list, listNamespaces.

Uses DOCKER_API_KEY from .env (preferred) via mcp_dockerhub_wrapper.ps1.
Does not print secret values.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        out[key.strip()] = value
    return out


def _redact(text: str) -> str:
    return re.sub(r"dckr_pat_[A-Za-z0-9_-]+", "dckr_pat_<redacted>", text)


def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    env = _parse_env(repo / ".env")
    token = env.get("DOCKER_API_KEY") or env.get("HUB_PAT_TOKEN")
    if not token:
        print("FAIL missing DOCKER_API_KEY/HUB_PAT_TOKEN in .env")
        return 1

    pwsh = shutil.which("pwsh")
    if not pwsh:
        print("FAIL pwsh not found")
        return 1

    wrapper = repo / "scripts" / "ai" / "mcp" / "mcp_dockerhub_wrapper.ps1"
    proc_env = os.environ.copy()
    proc_env.pop("HUB_PAT_TOKEN", None)
    proc_env["DOCKER_API_KEY"] = token
    proc_env["DOCKERHUB_USERNAME"] = env.get("DOCKERHUB_USERNAME", "satorykono")

    process = subprocess.Popen(
        [pwsh, "-NoProfile", "-File", str(wrapper)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=proc_env,
        cwd=str(repo),
        bufsize=1,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    stderr_chunks: list[str] = []

    def _drain_stderr() -> None:
        for line in process.stderr:
            stderr_chunks.append(line)

    threading.Thread(target=_drain_stderr, daemon=True).start()

    def send(message: dict[str, object]) -> None:
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    def read_json(timeout: float = 90.0) -> dict[str, object] | None:
        box: dict[str, str | None] = {"line": None}

        def reader() -> None:
            box["line"] = process.stdout.readline()

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        thread.join(timeout)
        if thread.is_alive() or not box["line"]:
            return None
        return json.loads(box["line"])

    try:
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "bioetl-dockerhub-smoke",
                        "version": "1.0.0",
                    },
                },
            }
        )
        init = read_json(90)
        if not init or "result" not in init:
            print("FAIL initialize", init)
            print(_redact("".join(stderr_chunks)[-1200:]))
            return 2
        result = init["result"]
        assert isinstance(result, dict)
        server_info = result.get("serverInfo", {})
        assert isinstance(server_info, dict)
        print("OK initialize", server_info.get("name"))

        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        tools_msg: dict[str, object] | None = None
        for _ in range(20):
            message = read_json(30)
            if not message:
                break
            if message.get("id") == 2:
                tools_msg = message
                break
        if not tools_msg or "result" not in tools_msg:
            print("FAIL tools/list")
            print(_redact("".join(stderr_chunks)[-1200:]))
            return 3
        tools_result = tools_msg["result"]
        assert isinstance(tools_result, dict)
        tools = tools_result.get("tools", [])
        assert isinstance(tools, list)
        names = sorted(
            str(tool["name"])
            for tool in tools
            if isinstance(tool, dict) and "name" in tool
        )
        print("OK tools/list", len(names), names[:10])

        if "listNamespaces" in names:
            call_name = "listNamespaces"
        elif "getPersonalNamespace" in names:
            call_name = "getPersonalNamespace"
        else:
            print("FAIL no namespace tool among", names)
            return 4

        send(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": call_name, "arguments": {}},
            }
        )
        call_msg: dict[str, object] | None = None
        for _ in range(30):
            message = read_json(60)
            if not message:
                break
            if message.get("id") == 3:
                call_msg = message
                break
        if not call_msg:
            print("FAIL tools/call timeout")
            print(_redact("".join(stderr_chunks)[-1200:]))
            return 5
        if "error" in call_msg:
            print("FAIL tools/call", _redact(json.dumps(call_msg["error"])[:500]))
            return 6

        call_result = call_msg.get("result", {})
        texts: list[str] = []
        if isinstance(call_result, dict):
            content = call_result.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(str(item.get("text", ""))[:300])
        preview = _redact(" | ".join(texts)[:500])
        print("OK tools/call", call_name)
        print("preview", preview)
        # Some gateway tools return transport errors as text content (HTTP 200 style).
        if re.search(
            r"(?i)\berror\b|fetch failed|unauthorized|invalid token|401|403",
            preview,
        ):
            print("RESULT tool_content_error")
            return 7
        print("RESULT ok")
        return 0
    finally:
        try:
            process.kill()
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
