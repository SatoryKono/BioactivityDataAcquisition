"""Bounded Linux stdio adapter for the isolated public-fetch-v1 runtime.

Use the pinned environment's Python with -I -S -B. The official Fetch package
provides its catalogue, argument validation, robots policy and extraction;
this adapter preserves the Windows owner's protocol and resource limits.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import importlib.metadata
import ipaddress
import json
import logging
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from mcp.server import MCPServer

MAX_INPUT = 64 * 1024
MAX_FRAME = 1024 * 1024
MAX_PENDING = 4
CALL_SECONDS = 38
QUEUE_SECONDS = 4
PROTOCOL = "2025-11-25"
TOOLS_CALL = "tools/call"
PROMPTS_GET = "prompts/get"


def load_backend() -> MCPServer:
    """Load only the isolated wheel installation, then bind public egress."""
    for package, expected in {"mcp-server-fetch": "2026.11.4", "mcp": "2.3.0"}.items():
        if importlib.metadata.version(package) != expected:
            raise RuntimeError("Pinned Fetch dependency changed")
    from mcp_server_fetch import server

    from public_fetch_transport import client_factory

    original = server._is_public_address

    def permitted(address: str) -> bool:
        # The reviewed Windows overlay adds fec0::/10 to upstream's denylist.
        ip = ipaddress.ip_address(address)
        return original(address) and not (
            isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local
        )

    server._is_public_address = permitted
    server.make_client = client_factory(server._resolve_host, permitted)
    return server.create_server(use_readability_js=False)


def respond(
    identifier: int | str | None,
    *,
    result: dict[str, object] | None = None,
    error: dict[str, object] | None = None,
) -> None:
    reply = {"jsonrpc": "2.0", "id": identifier}
    reply["error" if error is not None else "result"] = (
        error if error is not None else result
    )
    encoded = json.dumps(reply, ensure_ascii=True).encode("ascii")
    if len(encoded) > MAX_FRAME:
        encoded = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": identifier,
                "error": {
                    "code": -32000,
                    "message": "Fetch response exceeds the frame limit",
                },
            }
        ).encode("ascii")
    sys.stdout.buffer.write(encoded + b"\n")
    sys.stdout.buffer.flush()


async def invoke(
    instance: MCPServer, method: str, params: dict[str, object]
) -> dict[str, object]:
    if method == "tools/list":
        return {
            "tools": [
                item.model_dump(mode="json", by_alias=True, exclude_none=True)
                for item in await instance.list_tools()
            ]
        }
    if method == "prompts/list":
        return {
            "prompts": [
                item.model_dump(mode="json", by_alias=True, exclude_none=True)
                for item in await instance.list_prompts()
            ]
        }
    if params.get("name") != "fetch":
        raise ValueError("Unknown Fetch tool or prompt")
    arguments = params.get("arguments", {})
    url = arguments.get("url") if isinstance(arguments, dict) else None
    if not isinstance(url, str) or len(url) > 8192:
        raise ValueError("A bounded HTTP or HTTPS URL is required")
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.port not in {None, 80, 443}
    ):
        raise ValueError("Destination outside the public profile")
    async with asyncio.timeout(CALL_SECONDS):
        value = (
            await instance.call_tool("fetch", arguments)
            if method == TOOLS_CALL
            else await instance.get_prompt("fetch", arguments)
        )
    result = value.model_dump(mode="json", by_alias=True, exclude_none=True)
    result.pop("resultType", None)
    return result


async def invoke_serialized(
    instance: MCPServer,
    method: str,
    params: dict[str, object],
    active: asyncio.Lock,
) -> dict[str, object]:
    if method not in {TOOLS_CALL, PROMPTS_GET}:
        return await invoke(instance, method, params)
    # The Windows owner admits one backend operation at a time. Bound the
    # waiting queue as well, without extending the outer call deadline.
    async with asyncio.timeout(CALL_SECONDS):
        try:
            await asyncio.wait_for(active.acquire(), QUEUE_SECONDS)
        except TimeoutError:
            if method == PROMPTS_GET:
                raise
            return {
                "content": [{"type": "text", "text": "Fetch busy; request not sent"}],
                "isError": True,
            }
        try:
            return await invoke(instance, method, params)
        finally:
            active.release()


class StdioSession:
    def __init__(self, instance: MCPServer, tool_error: type[Exception]) -> None:
        self.instance = instance
        self.tool_error = tool_error
        self.pending: dict[int | str, asyncio.Task[None]] = {}
        self.active = asyncio.Lock()

    async def dispatch(
        self, identifier: int | str, method: str, params: dict[str, object]
    ) -> None:
        try:
            result = await invoke_serialized(self.instance, method, params, self.active)
            respond(identifier, result=result)
        except asyncio.CancelledError:
            raise
        except (self.tool_error, TimeoutError):
            if method == PROMPTS_GET:
                respond(
                    identifier,
                    error={
                        "code": -32000,
                        "message": "Fetch prompt refused or timed out; request not retried",
                    },
                )
                return
            respond(
                identifier,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": "Fetch refused or timed out; request not retried",
                        }
                    ],
                    "isError": True,
                },
            )
        except ValueError:
            respond(
                identifier,
                error={"code": -32602, "message": "Invalid public Fetch parameters"},
            )
        except Exception:
            # Upstream failures may contain URLs or environment details.
            respond(
                identifier,
                error={
                    "code": -32000,
                    "message": "Public Fetch failed; request not retried",
                },
            )
        finally:
            self.pending.pop(identifier, None)

    def accept(self, message: dict[str, object]) -> None:
        method, params = message.get("method"), message.get("params", {})
        if not isinstance(method, str) or not isinstance(params, dict):
            return
        identifier = message.get("id")
        if method == "notifications/cancelled" and "id" not in message:
            target = params.get("requestId")
            if type(target) in (int, str) and target in self.pending:
                self.pending[target].cancel()
            return
        if type(identifier) not in (int, str) or identifier in self.pending:
            return
        if method == "initialize":
            offered = params.get("protocolVersion")
            respond(
                identifier,
                result={
                    "protocolVersion": offered
                    if offered in ("2025-03-26", "2025-06-18", PROTOCOL)
                    else PROTOCOL,
                    "capabilities": {"tools": {}, "prompts": {}},
                    "serverInfo": {"name": "mcp-fetch", "version": "2026.11.4"},
                },
            )
        elif method == "ping":
            respond(identifier, result={})
        elif method in {"tools/list", TOOLS_CALL, "prompts/list", PROMPTS_GET}:
            self.schedule(identifier, method, params)
        else:
            respond(
                identifier, error={"code": -32601, "message": "Method not supported"}
            )

    def schedule(
        self, identifier: int | str, method: str, params: dict[str, object]
    ) -> None:
        if len(self.pending) >= MAX_PENDING:
            respond(
                identifier,
                error={"code": -32000, "message": "Too many pending Fetch requests"},
            )
        else:
            self.pending[identifier] = asyncio.create_task(
                self.dispatch(identifier, method, params)
            )

    async def close(self) -> None:
        tasks = list(self.pending.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def read_message(raw: bytes) -> dict[str, object] | None:
    if len(raw) > MAX_INPUT:
        while raw and not raw.endswith(b"\n"):
            raw = await asyncio.to_thread(sys.stdin.buffer.readline, MAX_INPUT + 1)
        respond(None, error={"code": -32600, "message": "Request too large"})
        return None
    try:
        message = json.loads(raw)
    except (ValueError, RecursionError):
        respond(None, error={"code": -32700, "message": "Invalid JSON"})
        return None
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return None
    return message


async def serve(instance: MCPServer, tool_error: type[Exception]) -> None:
    session = StdioSession(instance, tool_error)
    try:
        while raw := await asyncio.to_thread(sys.stdin.buffer.readline, MAX_INPUT + 1):
            message = await read_message(raw)
            if message is not None:
                session.accept(message)
    finally:
        await session.close()


def minimal_environment(environ: Mapping[str, str]) -> dict[str, str]:
    clean = {
        name: environ[name]
        for name in ("HOME", "SYSTEMROOT", "LANG", "LC_ALL")
        if name in environ
    }
    clean["PATH"] = "/usr/bin:/bin" if os.name != "nt" else ""
    return clean


async def terminate_worker(process: asyncio.subprocess.Process) -> None:
    """Keep the serial quota until the entire worker, including threads, exits."""
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    reaped = asyncio.create_task(process.wait())
    cancelled = False
    while not reaped.done():
        try:
            await asyncio.shield(reaped)
        except asyncio.CancelledError:
            cancelled = True
    reaped.result()
    if cancelled:
        raise asyncio.CancelledError


class WorkerResult:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def model_dump(self, **_kwargs: object) -> dict[str, object]:
        return dict(self.payload)


class WorkerBackend:
    """Run each SDK operation in a killable private process, never a thread."""

    def __init__(self, catalogue: MCPServer) -> None:
        self.catalogue = catalogue

    async def list_tools(self) -> object:
        return await self.catalogue.list_tools()

    async def list_prompts(self) -> object:
        return await self.catalogue.list_prompts()

    async def call_tool(self, name: str, arguments: object) -> WorkerResult:
        return await self.run(TOOLS_CALL, name, arguments)

    async def get_prompt(self, name: str, arguments: object) -> WorkerResult:
        return await self.run(PROMPTS_GET, name, arguments)

    async def run(self, method: str, name: str, arguments: object) -> WorkerResult:
        frame = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": {"name": name, "arguments": arguments},
            }
        ).encode()
        if len(frame) + 1 > MAX_INPUT:
            raise ValueError("Worker input exceeds the frame limit")
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(Path(__file__).resolve()),
            "--worker",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=MAX_FRAME + 1,
            env=minimal_environment(os.environ),
        )
        try:
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(frame + b"\n")
            await process.stdin.drain()
            process.stdin.close()
            raw = await process.stdout.readuntil(b"\n")
            if len(raw) > MAX_FRAME + 1 or await process.wait() != 0:
                raise RuntimeError("Fetch worker failed")
            reply = json.loads(raw)
            if reply.get("id") != 1 or not isinstance(reply.get("result"), dict):
                raise RuntimeError("Fetch worker refused the operation")
            return WorkerResult(reply["result"])
        finally:
            await terminate_worker(process)


async def run_worker(instance: MCPServer, tool_error: type[Exception]) -> None:
    """Consume exactly one bounded request on the private worker pipe."""
    raw = sys.stdin.buffer.readline(MAX_INPUT + 1)
    message = await read_message(raw)
    if message is None:
        return
    method, params = message.get("method"), message.get("params")
    if method not in (TOOLS_CALL, PROMPTS_GET) or not isinstance(params, dict):
        raise ValueError("Invalid worker operation")
    await StdioSession(instance, tool_error).dispatch(1, method, params)


def main() -> None:
    if (
        not sys.flags.isolated
        or not sys.flags.no_site
        or not sys.flags.dont_write_bytecode
        or sys.version_info[:2] != (3, 13)
        or sys.argv[1:] not in ([], ["--worker"])
    ):
        raise RuntimeError(
            "Use isolated pinned Python with -I -S -B and a supported mode"
        )
    # The orb holds unrelated provider secrets. Fetch receives no credentials,
    # proxy configuration, SDK settings or Python import overrides from it.
    clean = minimal_environment(os.environ)
    os.environ.clear()
    os.environ.update(clean)
    # The SDK configures HTTP request logging. URLs can carry sensitive query
    # values; expose only the bounded protocol results and generic CLI errors.
    logging.disable(logging.CRITICAL)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from public_fetch_runtime import bootstrap

    bootstrap()
    from mcp.server.mcpserver.exceptions import ToolError

    instance = load_backend()
    if sys.argv[1:] == ["--worker"]:
        asyncio.run(run_worker(instance, ToolError))
    else:
        asyncio.run(serve(WorkerBackend(instance), ToolError))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        sys.stderr.write("Public Fetch refused: " + type(error).__name__ + "\n")
        raise SystemExit(1) from None
