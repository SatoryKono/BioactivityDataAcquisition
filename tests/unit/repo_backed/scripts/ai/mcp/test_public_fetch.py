"""Public egress and real pinned-SDK probes; also runnable with isolated Python."""

from __future__ import annotations

import asyncio
import importlib.metadata
import importlib.util
import ipaddress
import io
import json
import os
from pathlib import Path
import socket
import sys
import queue
import threading
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[6]
SUPPORT = ROOT / "scripts/ai/mcp/support"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SUPPORT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = load("public_fetch_runtime")
S = load("public_fetch_stdio")
if __name__ == "__main__":
    clean_environment = S.minimal_environment(os.environ)
    os.environ.clear()
    os.environ.update(clean_environment)
    R.bootstrap()
    # The stdlib runner does not consume pytest markers or require pytest.
    pytest = SimpleNamespace(
        mark=SimpleNamespace(unit="unit", repo_backed="repo_backed")
    )
else:
    import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

import httpcore
import httpx

T = load("public_fetch_transport")


def permitted(value):
    ip = ipaddress.ip_address(value)
    return ip.is_global and not (
        isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local
    )


class Stream(httpcore.AsyncNetworkStream):
    def __init__(self, ip, port, response):
        self.peer = (ip, port)
        self.response = response
        self.writes = b""
        self.tls_host = None
        self.closed = False

    async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        assert ssl_context.check_hostname
        self.tls_host = server_hostname
        return self

    async def read(self, max_bytes, timeout=None):
        value, self.response = self.response[:max_bytes], self.response[max_bytes:]
        return value

    async def write(self, buffer, timeout=None):
        self.writes += buffer

    async def aclose(self):
        self.closed = True

    def get_extra_info(self, info):
        return self.peer if info == "server_addr" else None


class Connector:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []
        self.streams = []

    async def connect_tcp(self, host, port, **kwargs):
        self.calls.append((host, port))
        stream = Stream(host, port, next(self.responses))
        self.streams.append(stream)
        return stream


class TransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # The regular BioETL environment need not install the isolated SDK.
        # Actual pinned versions are checked separately by SDKTests below.
        pins = patch.object(T, "version", side_effect=T.PINS.__getitem__)
        pins.start()
        self.addCleanup(pins.stop)

    async def test_nonpublic_mixed_empty_excess_and_scoped_dns_never_connect(self):
        for addresses in [
            [],
            ["8.8.8.8", "127.0.0.1"],
            ["fec0::1"],
            ["fe80::1%lo"],
            [f"8.8.8.{number}" for number in range(1, 34)],
        ]:
            with self.subTest(addresses=addresses):
                connector = Connector()
                backend = T.PublicBackend(
                    AsyncMock(return_value=addresses), permitted, connector
                )
                with self.assertRaises(httpcore.ConnectError):
                    await backend.connect_tcp("fixture.invalid", 80)
                self.assertEqual(connector.calls, [])

    async def test_duplicate_socket_records_share_the_public_destination_limit(self):
        addresses = [f"8.8.8.{number}" for number in range(1, 17)] * 3
        connector = Connector(b"")
        backend = T.PublicBackend(
            AsyncMock(return_value=addresses), permitted, connector
        )
        stream = await backend.connect_tcp("fixture.invalid", 80)
        await stream.aclose()
        self.assertEqual(len(connector.calls), 1)
        backend = T.PublicBackend(
            AsyncMock(return_value=[*addresses, "127.0.0.1"]), permitted, Connector()
        )
        with self.assertRaises(httpcore.ConnectError):
            await backend.connect_tcp("fixture.invalid", 80)

    async def test_private_literal_port_local_bind_and_unix_are_refused(self):
        connector = Connector()
        resolver = AsyncMock(return_value=["8.8.8.8"])
        backend = T.PublicBackend(resolver, permitted, connector)
        for host, port, local in [
            ("127.0.0.1", 80, None),
            ("fixture.invalid", 8080, None),
            ("fixture.invalid", 80, "127.0.0.1"),
        ]:
            with self.assertRaises(httpcore.ConnectError):
                await backend.connect_tcp(host, port, local_address=local)
        with self.assertRaises(httpcore.ConnectError):
            await backend.connect_unix_socket("/fixture.sock")
        self.assertEqual(connector.calls, [])
        resolver.assert_not_awaited()

    async def test_dns_failure_and_connect_deadline_are_closed(self):
        backend = T.PublicBackend(
            AsyncMock(side_effect=socket.gaierror("fixture")), permitted, Connector()
        )
        with self.assertRaises(httpcore.ConnectError):
            await backend.connect_tcp("fixture.invalid", 443)

        async def slow(_host):
            await asyncio.sleep(1)
            return ["8.8.8.8"]

        backend = T.PublicBackend(slow, permitted, Connector())
        with self.assertRaises(httpcore.ConnectTimeout):
            await backend.connect_tcp("fixture.invalid", 443, timeout=0.001)

    async def test_connected_peer_must_match_ip_and_port(self):
        for peer in [None, ("127.0.0.1", 80), ("8.8.8.8", 443), ("invalid", 80)]:
            stream = Stream("8.8.8.8", 80, b"")
            stream.peer = peer
            connector = SimpleNamespace(connect_tcp=AsyncMock(return_value=stream))
            backend = T.PublicBackend(
                AsyncMock(return_value=["8.8.8.8"]), permitted, connector
            )
            with self.assertRaises(httpcore.ConnectError):
                await backend.connect_tcp("fixture.invalid", 80)
            self.assertTrue(stream.closed)
            self.assertFalse(stream.writes)

    async def test_literal_connection_keeps_tls_hostname_and_ignores_proxy_env(self):
        connector = Connector(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
        with (
            patch.object(httpcore, "AnyIOBackend", return_value=connector),
            patch.dict(
                os.environ,
                {
                    "HTTP_PROXY": "http://127.0.0.1:1080",
                    "HTTPS_PROXY": "http://127.0.0.1:1080",
                },
            ),
        ):
            make = T.client_factory(AsyncMock(return_value=["8.8.8.8"]), permitted)
            async with make(None) as client:
                result = await client.get("https://fixture.invalid/document")
            with self.assertRaises(ValueError):
                make("http://127.0.0.1:1080")
        self.assertEqual(result.text, "OK")
        self.assertEqual(connector.calls, [("8.8.8.8", 443)])
        self.assertEqual(connector.streams[0].tls_host, "fixture.invalid")
        self.assertIn(b"Host: fixture.invalid\r\n", connector.streams[0].writes)

    async def test_redirect_to_metadata_is_resolved_and_refused_before_connect(self):
        connector = Connector(
            b"HTTP/1.1 302 Found\r\nLocation: http://second.invalid/\r\nContent-Length: 0\r\n\r\n"
        )
        resolver = AsyncMock(side_effect=[["8.8.8.8"], ["169.254.169.254"]])
        with patch.object(httpcore, "AnyIOBackend", return_value=connector):
            async with T.client_factory(resolver, permitted)(None) as client:
                with self.assertRaises(httpx.ConnectError):
                    await client.get("http://first.invalid/", follow_redirects=True)
        self.assertEqual(connector.calls, [("8.8.8.8", 80)])
        self.assertEqual(
            [call.args[0] for call in resolver.await_args_list],
            ["first.invalid", "second.invalid"],
        )

    async def test_credentials_and_nonstandard_ports_are_refused_on_each_hop(self):
        for destination in [
            "http://fixture:password@second.invalid/",
            "http://second.invalid:8080/",
        ]:
            response = (
                "HTTP/1.1 302 Found\r\nLocation: "
                + destination
                + "\r\nContent-Length: 0\r\n\r\n"
            ).encode()
            connector = Connector(response)
            with patch.object(httpcore, "AnyIOBackend", return_value=connector):
                async with T.client_factory(
                    AsyncMock(return_value=["8.8.8.8"]), permitted
                )(None) as client:
                    with self.assertRaises(httpx.UnsupportedProtocol):
                        await client.get("http://first.invalid/", follow_redirects=True)
            self.assertEqual(connector.calls, [("8.8.8.8", 80)])

    async def test_encoded_declared_and_streamed_oversize_bodies_are_closed(self):
        for response in [
            b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Length: 2\r\n\r\nOK",
            b"HTTP/1.1 200 OK\r\nContent-Length: 9999999\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n"
            + b"x" * (T.MAX_BODY_BYTES + 1),
        ]:
            connector = Connector(response)
            with patch.object(httpcore, "AnyIOBackend", return_value=connector):
                async with T.client_factory(
                    AsyncMock(return_value=["8.8.8.8"]), permitted
                )(None) as client:
                    with self.assertRaises(httpx.ReadError):
                        await client.get("http://fixture.invalid/")
            self.assertTrue(connector.streams[0].closed)
            self.assertIn(b"Accept-Encoding: identity\r\n", connector.streams[0].writes)

    async def test_body_deadline_is_enforced(self):
        class Body(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b"OK"

        clock = SimpleNamespace(monotonic=iter([0.0, 16.0]).__next__)
        with patch.object(T, "time", clock):
            with self.assertRaises(httpx.ReadTimeout):
                _ = [
                    chunk
                    async for chunk in T.BoundedBody(
                        Body(), httpx.Request("GET", "https://fixture.invalid/")
                    )
                ]

    async def test_dependency_drift_is_refused(self):
        with patch.object(T, "version", return_value="0"):
            with self.assertRaises(RuntimeError):
                T.client_factory(AsyncMock(), permitted)

    async def test_request_deadline_wraps_httpx_send(self):
        actual = T.anyio.fail_after
        deadlines = []

        def short(seconds):
            deadlines.append(seconds)
            return actual(0.001)

        async def slow(*_args, **_kwargs):
            await asyncio.sleep(1)

        async with T.PublicClient() as client:
            with (
                patch.object(T.anyio, "fail_after", short),
                patch.object(httpx.AsyncClient, "send", slow),
            ):
                with self.assertRaises(httpx.ReadTimeout):
                    await client.send(httpx.Request("GET", "https://fixture.invalid/"))
        self.assertEqual(deadlines, [35])


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_busy_prompt_returns_protocol_error_without_calling_sdk(self):
        backend = SimpleNamespace(get_prompt=AsyncMock())
        session = S.StdioSession(backend, RuntimeError)
        await session.active.acquire()
        output = io.BytesIO()
        with (
            patch.object(S, "QUEUE_SECONDS", 0.001),
            patch.object(S.sys, "stdout", SimpleNamespace(buffer=output)),
        ):
            await session.dispatch(1, "prompts/get", {})
        session.active.release()
        reply = json.loads(output.getvalue())
        self.assertNotIn("result", reply)
        self.assertEqual(reply["error"]["code"], -32000)
        backend.get_prompt.assert_not_awaited()

    async def test_prompt_timeouts_and_tool_errors_return_protocol_errors(self):
        for error in (TimeoutError, RuntimeError):
            with self.subTest(error=error):
                backend = SimpleNamespace(get_prompt=AsyncMock(side_effect=error))
                session = S.StdioSession(backend, RuntimeError)
                output = io.BytesIO()
                with patch.object(S.sys, "stdout", SimpleNamespace(buffer=output)):
                    await session.dispatch(
                        1,
                        "prompts/get",
                        {"name": "fetch", "arguments": {"url": "https://example.com/"}},
                    )
                reply = json.loads(output.getvalue())
                self.assertNotIn("result", reply)
                self.assertEqual(reply["error"]["code"], -32000)
                self.assertFalse(session.active.locked())

    async def test_busy_queue_does_not_enter_sdk(self):
        active = asyncio.Lock()
        await active.acquire()
        backend = SimpleNamespace(call_tool=AsyncMock())
        with patch.object(S, "QUEUE_SECONDS", 0.001):
            result = await S.invoke_serialized(backend, "tools/call", {}, active)
        self.assertTrue(result["isError"])
        backend.call_tool.assert_not_awaited()
        active.release()

    async def test_cancelled_call_releases_the_serial_backend_slot(self):
        entered = asyncio.Event()

        async def slow(*_args):
            entered.set()
            await asyncio.Event().wait()

        active = asyncio.Lock()
        task = asyncio.create_task(
            S.invoke_serialized(
                SimpleNamespace(call_tool=slow),
                "tools/call",
                {"name": "fetch", "arguments": {"url": "https://example.com/"}},
                active,
            )
        )
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(active.locked())

    async def test_stdio_pending_limit_and_eof_cancel_all_work(self):
        incoming = queue.Queue()
        output = io.BytesIO()
        replied = threading.Event()

        class Input:
            def readline(self, _limit):
                return incoming.get(timeout=5)

        class Output:
            def write(self, value):
                output.write(value)
                replied.set()

            def flush(self):
                pass

        backend = SimpleNamespace(call_tool=AsyncMock(side_effect=lambda *_args: None))

        async def slow(*_args):
            await asyncio.Event().wait()

        backend.call_tool.side_effect = slow
        with (
            patch.object(
                asyncio,
                "to_thread",
                getattr(
                    asyncio.to_thread, "_bioetl_original_to_thread", asyncio.to_thread
                ),
            ),
            patch.object(S.sys, "stdin", SimpleNamespace(buffer=Input())),
            patch.object(S.sys, "stdout", SimpleNamespace(buffer=Output())),
        ):
            task = asyncio.create_task(S.serve(backend, RuntimeError))
            try:
                for identifier in range(5):
                    incoming.put(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": identifier,
                                "method": "tools/call",
                                "params": {
                                    "name": "fetch",
                                    "arguments": {"url": "https://example.com/"},
                                },
                            }
                        ).encode()
                        + b"\n"
                    )
                self.assertTrue(
                    await asyncio.wait_for(asyncio.to_thread(replied.wait, 2), 3)
                )
            finally:
                incoming.put(b"")
                await asyncio.wait_for(task, 2)
        replies = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["id"], 4)
        self.assertEqual(replies[0]["error"]["code"], -32000)
        self.assertEqual(backend.call_tool.await_count, 1)

    async def test_oversize_response_is_replaced_with_a_bounded_error(self):
        output = io.BytesIO()
        with patch.object(S.sys, "stdout", SimpleNamespace(buffer=output)):
            S.respond(1, result={"text": "x" * (S.MAX_FRAME + 1)})
        self.assertLess(len(output.getvalue()), S.MAX_FRAME)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], -32000)

    async def test_invalid_url_credentials_scheme_port_and_name_never_call_sdk(self):
        backend = SimpleNamespace(call_tool=AsyncMock())
        for url in [
            "file:///fixture",
            "http://fixture:password@example.com",
            "http://example.com:8080",
            "x" * 8193,
        ]:
            with self.assertRaises(ValueError):
                await S.invoke(
                    backend, "tools/call", {"name": "fetch", "arguments": {"url": url}}
                )
        with self.assertRaises(ValueError):
            await S.invoke(
                backend,
                "tools/call",
                {"name": "other", "arguments": {"url": "https://example.com/"}},
            )
        backend.call_tool.assert_not_awaited()

    async def test_outer_deadline_cancels_sdk_call(self):
        backend = SimpleNamespace(call_tool=AsyncMock(side_effect=asyncio.sleep))

        async def slow(*_args):
            await asyncio.sleep(1)

        backend.call_tool.side_effect = slow
        with patch.object(S, "CALL_SECONDS", 0.001):
            with self.assertRaises(TimeoutError):
                await S.invoke(
                    backend,
                    "tools/call",
                    {"name": "fetch", "arguments": {"url": "https://example.com/"}},
                )

    async def test_unrelated_credentials_proxy_and_import_overrides_are_scrubbed(self):
        clean = S.minimal_environment(
            {
                "HOME": "/fixture",
                "OPENAI_API_KEY": "unrelated-fixture-credential",
                "HTTPS_PROXY": "http://127.0.0.1",
                "PYTHONPATH": "/untrusted",
            }
        )
        self.assertEqual(set(clean), {"HOME", "PATH"})


class RuntimeIdentityTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "reports/local"
        scratch.mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(
            prefix="bioetl-fetch-profile-", dir=scratch
        )
        self.addCleanup(directory.cleanup)
        self.site = Path(directory.name)
        for name, version in [("mcp", "2.3.0"), ("mcp-server-fetch", "2026.11.4")]:
            metadata = self.site / (
                name.replace("-", "_") + "-" + version + ".dist-info"
            )
            metadata.mkdir()
            (metadata / "METADATA").write_text(
                f"Name: {name}\nVersion: {version}\n", encoding="utf-8"
            )
        self.code = self.site / "boundary.py"
        self.code.write_text("# reviewed fixture code\n", encoding="utf-8")
        self.flags = SimpleNamespace(
            isolated=True, no_site=True, dont_write_bytecode=True
        )
        self.fake_sys = SimpleNamespace(
            version_info=(3, 13), platform=sys.platform, flags=self.flags, path=[]
        )
        for scope in [
            patch.object(R, "package_directory", return_value=self.site),
            patch.object(R, "sys", self.fake_sys),
        ]:
            scope.start()
            self.addCleanup(scope.stop)

    def test_source_native_data_and_extra_files_all_change_identity(self):
        original = R.measure_runtime()["files_sha256"]
        self.code.write_text("# changed fixture code\n", encoding="utf-8")
        changed = R.measure_runtime()["files_sha256"]
        self.assertNotEqual(original, changed)
        (self.site / "extension.so").write_bytes(b"fixture native bytes; never loaded")
        self.assertNotEqual(changed, R.measure_runtime()["files_sha256"])

    def test_sourceless_bytecode_is_refused(self):
        (self.site / "unreviewed.pyc").write_bytes(b"fixture; never loaded")
        with self.assertRaises(RuntimeError):
            R.measure_runtime()

    def test_bootstrap_refuses_tampering_before_adding_import_paths(self):
        actual = R.measure_runtime()
        profile = self.site.parent / (self.site.name + "-profiles.json")
        self.addCleanup(profile.unlink, missing_ok=True)
        profile.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "requirements_sha256": actual["requirements_sha256"],
                    "profiles": {actual["platform"]: actual},
                }
            ),
            encoding="utf-8",
        )
        with patch.object(R, "PROFILES", profile):
            R.bootstrap()
            self.assertEqual(self.fake_sys.path, [str(self.site)])
            self.assertFalse(Path(self.fake_sys.pycache_prefix).exists())
            self.fake_sys.path.clear()
            self.code.write_text("# tampered fixture code\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                R.bootstrap()
        self.assertEqual(self.fake_sys.path, [])

    def test_missing_profile_and_changed_lock_fail_closed(self):
        actual = R.measure_runtime()
        profile = self.site.parent / (self.site.name + "-profiles.json")
        self.addCleanup(profile.unlink, missing_ok=True)
        for lock in [actual["requirements_sha256"], "0" * 64]:
            profile.write_text(
                json.dumps(
                    {"schema_version": 1, "requirements_sha256": lock, "profiles": {}}
                ),
                encoding="utf-8",
            )
            with patch.object(R, "PROFILES", profile):
                with self.assertRaises(RuntimeError):
                    R.bootstrap()
        self.assertEqual(self.fake_sys.path, [])

    def test_nonisolated_interpreter_fails_before_measurement(self):
        self.flags.no_site = False
        with patch.object(R, "measure_runtime") as measure:
            with self.assertRaises(RuntimeError):
                R.bootstrap()
        measure.assert_not_called()


@unittest.skipUnless(
    importlib.util.find_spec("mcp_server_fetch"),
    "Run the pinned isolated Fetch qualification for SDK probes",
)
class SDKTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_and_deadline_reap_real_html_extraction_before_releasing_slot(
        self,
    ):
        scratch = ROOT / "reports/local"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="fetch-worker-", dir=scratch
        ) as directory:
            folder = Path(directory)
            entered = folder / "entered.txt"
            worker = folder / "blocked_extractor.py"
            runtime = ROOT / "scripts/ai/mcp/support/public_fetch_runtime.py"
            worker.write_text(
                "import asyncio, importlib.util, pathlib, threading\n"
                f"spec=importlib.util.spec_from_file_location('runtime', {str(runtime)!r})\n"
                "runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)\n"
                "runtime.bootstrap()\n"
                "from mcp_server_fetch import server\n"
                "def blocked(html):\n"
                f" pathlib.Path({str(entered)!r}).write_text('actual extractor entered')\n"
                " threading.Event().wait()\n"
                "server._readability_content=blocked\n"
                "asyncio.run(asyncio.to_thread(server.extract_content_from_html, '<html><body>fixture</body></html>', False))\n",
                encoding="utf-8",
            )
            original = asyncio.create_subprocess_exec
            processes = []

            async def start_fixture(*args, **kwargs):
                self.assertTrue(all(p.returncode is not None for p in processes))
                process = await original(*args[:4], str(worker), **kwargs)
                processes.append(process)
                return process

            active = asyncio.Lock()
            backend = S.WorkerBackend(SimpleNamespace())
            with patch.object(S.asyncio, "create_subprocess_exec", start_fixture):
                for cancel in (True, False):
                    with (
                        self.subTest(cancel=cancel),
                        patch.object(S, "CALL_SECONDS", 8),
                    ):
                        entered.unlink(missing_ok=True)
                        task = asyncio.create_task(
                            S.invoke_serialized(
                                backend,
                                "tools/call",
                                {
                                    "name": "fetch",
                                    "arguments": {"url": "https://example.com/"},
                                },
                                active,
                            )
                        )
                        try:
                            async with asyncio.timeout(7):
                                while not entered.exists():
                                    await asyncio.sleep(0.02)
                            self.assertTrue(active.locked())
                            if cancel:
                                task.cancel()
                            with self.assertRaises(
                                asyncio.CancelledError if cancel else TimeoutError
                            ):
                                await task
                        finally:
                            if not task.done():
                                task.cancel()
                                await asyncio.gather(task, return_exceptions=True)
                        self.assertIsNotNone(processes[-1].returncode)
                        self.assertFalse(active.locked())

    async def test_pinned_versions_and_site_local_policy(self):
        for name, expected in {
            **T.PINS,
            "mcp": "2.3.0",
            "mcp-server-fetch": "2026.11.4",
        }.items():
            self.assertEqual(importlib.metadata.version(name), expected)
        S.load_backend()
        from mcp_server_fetch import server

        for address in [
            "127.0.0.1",
            "10.1.2.3",
            "169.254.169.254",
            "::1",
            "fec0::1",
            "fe80::1",
            "::ffff:127.0.0.1",
        ]:
            self.assertFalse(server._is_public_address(address), address)
        self.assertTrue(server._is_public_address("8.8.8.8"))

    async def test_dns_rebinding_is_refused_by_real_fetch_handler(self):
        from mcp_server_fetch import server
        from mcp.server.mcpserver.exceptions import ToolError

        connector = Connector()
        resolver = AsyncMock(side_effect=[["8.8.8.8"], ["169.254.169.254"]])
        with (
            patch.object(httpcore, "AnyIOBackend", return_value=connector),
            patch.object(server, "_resolve_host", resolver),
        ):
            instance = S.load_backend()
            with self.assertRaises(ToolError):
                await S.invoke(
                    instance,
                    "tools/call",
                    {"name": "fetch", "arguments": {"url": "http://fixture.invalid/"}},
                )
        self.assertEqual(resolver.await_count, 2)
        self.assertEqual(connector.calls, [])

    async def test_real_sdk_public_call_through_pinned_transport(self):
        from mcp_server_fetch import server

        connector = Connector(
            b"HTTP/1.1 200 OK\r\nContent-Length: 22\r\n\r\nUser-agent: *\nAllow: /\n",
            b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK",
        )
        with (
            patch.object(httpcore, "AnyIOBackend", return_value=connector),
            patch.object(server, "_resolve_host", AsyncMock(return_value=["8.8.8.8"])),
        ):
            result = await S.invoke(
                S.load_backend(),
                "tools/call",
                {
                    "name": "fetch",
                    "arguments": {
                        "url": "https://fixture.invalid/document",
                        "raw": True,
                    },
                },
            )
        self.assertFalse(result.get("isError", False), result)
        self.assertIn("OK", json.dumps(result))
        self.assertTrue(connector.calls)
        self.assertTrue(all(host == "8.8.8.8" for host, _port in connector.calls))

    async def test_real_stdio_initialize_catalogue_private_call_and_input_limit(self):
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(SUPPORT / "public_fetch_stdio.py"),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=S.minimal_environment(os.environ),
        )

        async def rpc(identifier, method, params=None):
            process.stdin.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": identifier,
                        "method": method,
                        "params": params or {},
                    }
                ).encode()
                + b"\n"
            )
            await process.stdin.drain()
            line = await asyncio.wait_for(process.stdout.readline(), 15)
            self.assertTrue(line, "Pinned stdio process closed before replying")
            return json.loads(line)

        try:
            hello = await rpc(
                1,
                "initialize",
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "fixture", "version": "1"},
                },
            )
            self.assertEqual(hello["result"]["protocolVersion"], "2025-11-25")
            malformed = await rpc(7, "initialize", {"protocolVersion": []})
            self.assertEqual(malformed["result"]["protocolVersion"], "2025-11-25")
            tools = await rpc(2, "tools/list")
            expected = json.loads(
                (ROOT / "tests/fixtures/mcp/public-fetch-catalogue.json").read_text()
            )
            self.assertEqual(tools["result"]["tools"], expected["tools"])
            denied = await rpc(
                3,
                "tools/call",
                {"name": "fetch", "arguments": {"url": "http://127.0.0.1/"}},
            )
            self.assertTrue(denied["result"]["isError"])
            process.stdin.write(b"x" * (S.MAX_INPUT + 1) + b"\n")
            await process.stdin.drain()
            refused = json.loads(await asyncio.wait_for(process.stdout.readline(), 5))
            self.assertEqual(refused["error"]["code"], -32600)
            self.assertEqual((await rpc(4, "ping"))["result"], {})
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), 10)
            except TimeoutError:
                process.kill()
                await process.wait()
        self.assertEqual(process.returncode, 0, (await process.stderr.read()).decode())


if __name__ == "__main__":
    unittest.main(verbosity=2)
