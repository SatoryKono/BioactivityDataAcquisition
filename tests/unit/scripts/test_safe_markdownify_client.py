"""A private protocol connection cannot create a persistent service owner."""

from email.message import Message
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, StringIO, TextIOWrapper
import json
from threading import Event, Lock
from unittest.mock import Mock
from types import SimpleNamespace

import pytest

from scripts.ai.mcp import safe_markdownify as markdownify

pytestmark = pytest.mark.unit


def test_client_connects_only_to_a_preexisting_ready_owner(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(markdownify, "specification", lambda root: {"root": root})

    def request(spec, method, path, *args):
        calls.append((method, path))
        return {"ready": True}, None

    monkeypatch.setattr(markdownify, "request", request)
    monkeypatch.setattr(markdownify.sys, "stdin", StringIO(""))
    monkeypatch.setattr(
        markdownify,
        "ensure",
        lambda *_: pytest.fail("client started a persistent owner"),
    )
    markdownify.client(tmp_path)
    assert calls == [("GET", "/health")]


def test_unready_owner_does_not_trigger_an_implicit_start(tmp_path, monkeypatch):
    monkeypatch.setattr(markdownify, "specification", lambda root: {"root": root})
    monkeypatch.setattr(markdownify, "request", lambda *_: ({"ready": False}, None))
    monkeypatch.setattr(
        markdownify,
        "ensure",
        lambda *_: pytest.fail("client started a persistent owner"),
    )
    with pytest.raises(PermissionError, match="administrative"):
        markdownify.client(tmp_path)


@pytest.fixture
def handler(tmp_path, monkeypatch):
    """Exercise the request handler without binding a socket or starting an owner."""
    monkeypatch.setattr(
        markdownify.BaseHTTPRequestHandler, "__init__", lambda *a, **k: None
    )
    spec = {"enabled_tools": ["get-markdown-file"]}
    instance = markdownify._MarkdownifyHandler(
        None,
        None,
        None,
        workspace=tmp_path,
        spec=spec,
        record={"generation": "reviewed-generation"},
        token="fixture-token",
        sessions=markdownify._SessionRegistry(),
        gate=Lock(),
        draining=Event(),
    )
    instance.headers = Message()
    instance.headers["Authorization"] = "Bearer fixture-token"
    instance.reply = Mock()
    monkeypatch.setattr(markdownify, "specification", lambda root: spec)
    monkeypatch.setattr(
        markdownify, "ensure", lambda *_: pytest.fail("unexpected owner launch")
    )
    return instance


def test_protocol_initialization_and_tool_visibility_remain_session_bound(handler):
    handler._dispatch_request({"id": 1, "method": "initialize"})
    status, response, session = handler.reply.call_args.args
    assert status == 200
    assert response["result"]["protocolVersion"] == "2025-06-18"
    assert handler._sessions.touch(session)
    handler.headers["Mcp-Session-Id"] = session
    handler._dispatch_request({"id": 2, "method": "tools/list"})
    assert [
        tool["name"] for tool in handler.reply.call_args.args[1]["result"]["tools"]
    ] == ["get-markdown-file"]
    handler.do_DELETE()
    assert not handler._sessions.touch(session)
    handler._dispatch_request({"id": 3, "method": "ping"})
    handler.reply.assert_called_with(404)


def test_protocol_authentication_and_body_limit_fail_before_reading(handler):
    del handler.headers["Authorization"]
    handler.path = "/mcp"
    handler.rfile = Mock()
    handler.do_POST()
    handler.reply.assert_called_with(401)
    handler.rfile.read.assert_not_called()
    handler.headers["Authorization"] = "Bearer fixture-token"
    handler.headers["Content-Length"] = str(1024 * 1024 + 1)
    handler.do_POST()
    handler.reply.assert_called_with(413)
    handler.rfile.read.assert_not_called()


def test_protocol_get_rejects_other_paths_and_preserves_generation(handler):
    handler.path = markdownify.HEALTH_PATH
    handler.do_GET()
    assert handler.reply.call_args.args[1]["generation"] == "reviewed-generation"
    handler.path = "/foreign"
    handler.do_GET()
    handler.reply.assert_called_with(405)


def test_protocol_tool_failures_are_redacted_and_draining_blocks_conversion(
    handler, monkeypatch
):
    convert = Mock(side_effect=PermissionError("private/file/path"))
    monkeypatch.setattr(markdownify, "convert", convert)
    request = {
        "params": {
            "name": "get-markdown-file",
            "arguments": {"filepath": "private/file/path"},
        }
    }
    result = handler._call_tool(request)
    assert result == {
        "isError": True,
        "content": [{"type": "text", "text": "Local file access/conversion refused"}],
    }
    handler._draining.set()
    convert.reset_mock()
    assert handler._call_tool(request) == result
    convert.assert_not_called()


def test_protocol_session_limit_and_notification_semantics(handler):
    sessions = [handler._sessions.issue() for _ in range(64)]
    handler._dispatch_request({"id": 1, "method": "initialize"})
    handler.reply.assert_called_with(503)
    handler.headers["Mcp-Session-Id"] = sessions[0]
    handler._dispatch_request({"method": "notifications/initialized"})
    handler.reply.assert_called_with(202)


def test_protocol_post_dispatches_bounded_json(handler):
    raw = b'{"id": 1, "method": "initialize"}'
    handler.path = "/mcp"
    handler.headers["Content-Length"] = str(len(raw))
    handler.rfile = BytesIO(raw)
    handler.do_POST()
    assert handler.reply.call_args.args[0] == 200
    assert handler.rfile.tell() == len(raw)


def test_unicode_conversion_response_fits_the_existing_client_bound(
    handler, monkeypatch
):
    text = "я" * 400_000
    monkeypatch.setattr(markdownify, "convert", lambda *_: text)
    result = handler._call_tool({"params": {"name": "docx-to-markdown"}})
    value = {"jsonrpc": "2.0", "id": 1, "result": result}
    raw = markdownify._response_bytes(value)
    assert len(raw) < markdownify.MAX_RESPONSE_BYTES
    assert json.loads(raw)["result"]["content"][0]["text"] == text


def test_oversized_json_envelope_returns_bounded_tool_error():
    value = {
        "jsonrpc": "2.0",
        "id": 12,
        "result": {
            "content": [{"type": "text", "text": "x" * markdownify.MAX_RESPONSE_BYTES}]
        },
    }
    raw = markdownify._response_bytes(value)
    assert len(raw) <= markdownify.MAX_RESPONSE_BYTES
    result = json.loads(raw)
    assert result["id"] == 12
    assert result["result"]["isError"] is True
    assert "x" * 100 not in raw.decode()


def test_oversized_escaped_identifier_cannot_defeat_response_bound():
    raw = markdownify._response_bytes({"id": "\x00" * 400_000})
    assert len(raw) <= markdownify.MAX_RESPONSE_BYTES
    value = json.loads(raw)
    assert value["id"] is None
    assert value["result"]["isError"] is True


def test_response_preserves_escaped_surrogate_identifier():
    value = {"jsonrpc": "2.0", "id": "\ud800", "result": {}}
    assert json.loads(markdownify._response_bytes(value)) == value


def test_orphan_sessions_expire_without_restarting_owner():
    now = [0.0]
    sessions = markdownify._SessionRegistry(clock=lambda: now[0])
    orphaned = [sessions.issue() for _ in range(markdownify.SESSION_LIMIT)]
    assert sessions.issue() is None
    now[0] = markdownify.SESSION_IDLE_SECONDS
    replacement = sessions.issue()
    assert replacement is not None
    assert all(not sessions.touch(session) for session in orphaned)
    assert sessions.touch(replacement)


def test_active_session_renews_lease_and_discard_reclaims_capacity():
    now = [0.0]
    sessions = markdownify._SessionRegistry(clock=lambda: now[0])
    active = sessions.issue()
    now[0] = markdownify.SESSION_IDLE_SECONDS - 1
    assert sessions.touch(active)
    now[0] += 2
    assert sessions.touch(active)
    sessions.discard(active)
    assert not sessions.touch(active)


def test_concurrent_initialization_cannot_exceed_existing_session_limit():
    sessions = markdownify._SessionRegistry()
    with ThreadPoolExecutor(max_workers=8) as executor:
        issued = list(executor.map(lambda _: sessions.issue(), range(128)))
    accepted = [session for session in issued if session is not None]
    assert len(accepted) == len(set(accepted)) == markdownify.SESSION_LIMIT


def test_metadata_available_format_is_disabled_when_the_frozen_probe_fails(monkeypatch):
    attempts = []

    def convert(spec, extension, raw):
        attempts.append((extension, raw))
        if extension == ".pdf":
            raise ValueError("converter dependency imports fail")
        if extension == ".xlsx":
            return "conversion returned no expected content"
        return markdownify.snapshots.QUALIFICATION_TEXT

    monkeypatch.setattr(markdownify, "_convert_bytes", convert)
    spec = {"converter": "frozen-converter"}
    evidence = markdownify._qualify_converter(spec, {"pdf", "docx", "xlsx"})
    assert evidence["results"] == {
        "pdf-to-markdown": "FAIL",
        "docx-to-markdown": "PASS",
        "pptx-to-markdown": "UNAVAILABLE",
        "xlsx-to-markdown": "FAIL",
        "html-to-markdown": "PASS",
        "get-markdown-file": "PASS",
    }
    assert {extension for extension, _ in attempts} == {
        ".pdf",
        ".docx",
        ".xlsx",
        ".html",
    }
    spec.update(
        qualification=evidence, enabled_tools=markdownify._enabled_tools(evidence)
    )
    assert markdownify._qualification_matches(spec)
    spec["enabled_tools"].append("pdf-to-markdown")
    assert not markdownify._qualification_matches(spec)


def test_probe_timeouts_disable_the_format_without_enabling_metadata_fallback(
    monkeypatch,
):
    from subprocess import TimeoutExpired

    def timeout(*args):
        raise TimeoutExpired("owned converter", 90)

    monkeypatch.setattr(markdownify, "_convert_bytes", timeout)
    evidence = markdownify._qualify_converter({"converter": "pinned"}, {"pdf"})
    assert markdownify._enabled_tools(evidence) == ["get-markdown-file"]


def test_qualification_cannot_be_reused_for_another_converter():
    evidence = {
        "schema": 1,
        "converter": "previous-snapshot",
        "results": dict.fromkeys(markdownify.EXTENSIONS, "PASS"),
    }
    spec = {
        "converter": "new-snapshot",
        "qualification": evidence,
        "enabled_tools": list(markdownify.EXTENSIONS),
    }
    assert not markdownify._qualification_matches(spec)


def test_conversion_and_qualification_share_the_same_owned_worker(
    monkeypatch, tmp_path
):
    raw = b"synthetic source content"
    monkeypatch.setattr(markdownify.files, "read_confined", lambda *_: raw)
    worker = Mock(return_value="converted content")
    monkeypatch.setattr(markdownify, "_convert_bytes", worker)
    spec = {"enabled_tools": ["pdf-to-markdown"], "binding": {"root": str(tmp_path)}}
    assert (
        markdownify.convert(spec, "pdf-to-markdown", {"filepath": "probe.pdf"})
        == "converted content"
    )
    worker.assert_called_once_with(spec, ".pdf", raw)


@pytest.mark.parametrize("extension", [".docx", ".pptx", ".xlsx"])
def test_office_qualification_samples_are_self_contained_packages(extension):
    import zipfile
    import xml.etree.ElementTree as ET

    raw = markdownify.snapshots.qualification_sample(extension)
    with zipfile.ZipFile(BytesIO(raw)) as package:
        names = package.namelist()
        assert "[Content_Types].xml" in names and "_rels/.rels" in names
        for name in names:
            ET.fromstring(package.read(name))
        assert any(
            markdownify.snapshots.QUALIFICATION_TEXT.encode() in package.read(name)
            for name in names
        )
        assert all(
            not name.startswith("/") and ".." not in name.split("/") for name in names
        )


def test_prepare_publishes_only_formats_that_passed_the_frozen_probe(
    tmp_path, monkeypatch
):
    from contextlib import nullcontext
    from types import SimpleNamespace

    state = tmp_path / "private-state"
    state.mkdir()
    written = {}
    core = SimpleNamespace(
        STATE=state,
        private_directory=lambda: None,
        LifetimeLock=lambda _: nullcontext(),
        credential=lambda **_: "unused-fixture",
        write_json=lambda path, value: written.update(value),
    )
    monkeypatch.setattr(markdownify, "core", core)
    monkeypatch.setattr(
        markdownify, "configure", lambda _: ("id", {"root": str(tmp_path)})
    )
    monkeypatch.setattr(markdownify.snapshots, "closure", lambda *args: None)
    monkeypatch.setattr(
        markdownify.snapshots, "build", lambda *args: tmp_path / "frozen"
    )
    monkeypatch.setattr(markdownify, "pins", lambda _: {"pinned": "digest"})
    sock = Mock()
    sock.getsockname.return_value = ("127.0.0.1", 12345)
    manager = Mock()
    manager.__enter__ = Mock(return_value=sock)
    manager.__exit__ = Mock(return_value=None)
    monkeypatch.setattr(markdownify.socket, "socket", lambda: manager)
    monkeypatch.setattr(markdownify.socket, "SO_EXCLUSIVEADDRUSE", 0, raising=False)

    def convert(spec, extension, raw):
        if extension == ".html":
            return markdownify.snapshots.QUALIFICATION_TEXT
        raise ValueError("metadata was present but worker failed")

    monkeypatch.setattr(markdownify, "_convert_bytes", convert)
    profile = markdownify.prepare(tmp_path)
    assert profile["enabled_tools"] == ["html-to-markdown", "get-markdown-file"]
    assert profile == written
    assert markdownify._qualification_matches(profile)


def test_busy_conversion_is_not_queued_or_executed(handler, monkeypatch):
    convert = Mock()
    monkeypatch.setattr(markdownify, "convert", convert)
    with handler._gate:
        result = handler._call_tool({"params": {"name": "pdf-to-markdown"}})
    assert result["isError"] and "busy" in result["content"][0]["text"]
    convert.assert_not_called()


def test_stale_stop_marker_does_not_end_the_generation_watcher(tmp_path, monkeypatch):
    from types import SimpleNamespace

    marker = tmp_path / markdownify.STOP_REQUEST
    marker.write_text('{"generation": "previous"}', encoding="utf-8")
    monkeypatch.setattr(
        markdownify,
        "core",
        SimpleNamespace(
            STATE=tmp_path, read_json=lambda path: json.loads(path.read_bytes())
        ),
    )
    sleeps = []

    def sleep(_):
        sleeps.append(True)
        marker.write_text('{"generation": "current"}', encoding="utf-8")

    monkeypatch.setattr(markdownify.time, "sleep", sleep)
    server, draining = Mock(), Event()
    markdownify._watch_stop(server, {"generation": "current"}, Lock(), draining)
    assert sleeps and draining.is_set()
    server.shutdown.assert_called_once_with()


def test_expired_inner_session_reinitializes_without_replaying_the_tool(monkeypatch):
    initialization = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    }
    original = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "pdf-to-markdown"},
    }
    calls = []

    def request(spec, method, path, value, session=None):
        calls.append((value, session))
        if value is original:
            raise markdownify._SessionExpired("fixture expiry")
        if value["method"] == "initialize":
            return {"result": {"protocolVersion": "2025-06-18"}}, "renewed"
        assert value["method"] == "notifications/initialized"
        return None, None

    monkeypatch.setattr(markdownify, "request", request)
    result, session = markdownify._forward_request(
        {}, original, "expired", initialization
    )
    assert session == "renewed" and result["id"] == 2 and "error" in result
    assert sum(value is original for value, _ in calls) == 1
    assert calls[1][1] is None and calls[2][1] == "renewed"
    assert calls[1][0]["params"] == initialization["params"]


def test_preauth_connections_have_a_capacity_and_an_absolute_read_deadline(monkeypatch):
    import socket
    from threading import Condition, Thread

    monkeypatch.setattr(markdownify, "HTTP_CONNECTION_LIMIT", 2)
    monkeypatch.setattr(markdownify, "HTTP_READ_SECONDS", 1)
    changed = Condition()
    active = [0]

    def handler(connection, *_):
        with changed:
            active[0] += 1
            changed.notify_all()
        try:
            while connection.recv(1):
                pass
        finally:
            with changed:
                active[0] -= 1
                changed.notify_all()

    server = markdownify._BoundedHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    connections = []
    try:
        for _ in range(2):
            connections.append(
                socket.create_connection(server.server_address, timeout=3)
            )
        with changed:
            assert changed.wait_for(lambda: active[0] == 2, timeout=3)
        extra = socket.create_connection(server.server_address, timeout=3)
        connections.append(extra)
        try:
            assert extra.recv(1) == b""
        except ConnectionResetError:
            pass
        with changed:
            assert changed.wait_for(lambda: active[0] == 0, timeout=3)
        assert server._slots.acquire(timeout=2)
        assert server._slots.acquire(timeout=2)
        assert not server._slots.acquire(blocking=False)
        server._slots.release()
        server._slots.release()
    finally:
        for connection in connections:
            connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    assert not thread.is_alive()


def test_busy_converter_refuses_without_waiting_or_running(handler, monkeypatch):
    convert = Mock()
    monkeypatch.setattr(markdownify, "convert", convert)
    assert handler._gate.acquire(blocking=False)
    try:
        result = handler._call_tool({"params": {"name": "get-markdown-file"}})
        assert result["isError"] is True
        assert "not queued" in result["content"][0]["text"]
        convert.assert_not_called()
    finally:
        handler._gate.release()


def test_connection_cap_applies_before_handler_thread_creation(monkeypatch):
    server = object.__new__(markdownify._BoundedHTTPServer)
    server._slots = markdownify.threading.BoundedSemaphore(2)
    server._deadlines = {}
    server._expired_readers = set()
    server._deadline_lock = Lock()
    requests = {name: Mock() for name in ("first", "second", "excess", "replacement")}
    server.shutdown_request = Mock()
    start = Mock()
    monkeypatch.setattr(markdownify.ThreadingHTTPServer, "process_request", start)
    server.process_request(requests["first"], None)
    server.process_request(requests["second"], None)
    server.process_request(requests["excess"], None)
    assert start.call_count == 2
    server.shutdown_request.assert_called_once_with(requests["excess"])
    worker = Mock(side_effect=RuntimeError("handler failure"))
    monkeypatch.setattr(
        markdownify.ThreadingHTTPServer, "process_request_thread", worker
    )
    with pytest.raises(RuntimeError, match="handler failure"):
        server.process_request_thread(requests["first"], None)
    server.process_request(requests["replacement"], None)
    assert start.call_count == 3


def test_failed_thread_start_releases_connection_capacity(monkeypatch):
    server = object.__new__(markdownify._BoundedHTTPServer)
    server._slots = markdownify.threading.BoundedSemaphore(1)
    server.shutdown_request = Mock()
    monkeypatch.setattr(
        markdownify.ThreadingHTTPServer,
        "process_request",
        Mock(side_effect=RuntimeError("cannot start thread")),
    )
    with pytest.raises(RuntimeError, match="cannot start thread"):
        server.process_request(Mock(), None)
    assert server._slots.acquire(blocking=False)


def test_read_deadline_cannot_dispatch_after_expiration():
    server = object.__new__(markdownify._BoundedHTTPServer)
    server._deadlines = {}
    server._expired_readers = set()
    server._deadline_lock = Lock()
    connection, timer = Mock(), Mock()
    server._deadlines[connection] = timer
    server._expire_reader(connection)
    with pytest.raises(TimeoutError):
        server.finish_reading(connection, completed=True)
    connection.shutdown.assert_called_once_with(markdownify.socket.SHUT_RDWR)
    timer.cancel.assert_called_once()
    connection.reset_mock()
    server._deadlines[connection] = Mock()
    server.finish_reading(connection, completed=True)
    server._expire_reader(connection)
    connection.shutdown.assert_not_called()


def test_foreign_stop_marker_does_not_disable_current_generation_watcher(
    tmp_path, monkeypatch
):
    (tmp_path / markdownify.STOP_REQUEST).write_text("{}", encoding="utf-8")
    requests = iter([{"generation": "old"}, {"generation": "current"}])
    monkeypatch.setattr(
        markdownify,
        "core",
        SimpleNamespace(STATE=tmp_path, read_json=lambda _: next(requests)),
    )
    sleep = Mock()
    monkeypatch.setattr(markdownify.time, "sleep", sleep)
    server, draining = Mock(), Event()
    markdownify._watch_stop(server, {"generation": "current"}, Lock(), draining)
    assert draining.is_set()
    sleep.assert_called_once_with(0.2)
    server.shutdown.assert_called_once()


def test_expired_private_session_reinitializes_without_replaying_tool(
    tmp_path, monkeypatch, capsys
):
    calls = []
    monkeypatch.setattr(markdownify, "specification", lambda _: {})
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    }
    tool = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "get-markdown-file"},
    }

    def request(spec, method, path, body=None, session=None):
        calls.append((method, body, session))
        if method == "GET":
            return {"ready": True}, None
        if body == initialize:
            assert session is None
            return {"id": 1, "result": {}}, "new" if len(calls) > 3 else "old"
        if body == tool:
            raise markdownify._SessionExpired("expired")
        return None, None

    monkeypatch.setattr(markdownify, "request", request)
    monkeypatch.setattr(
        markdownify.sys,
        "stdin",
        StringIO(
            "\n".join(map(json.dumps, [initialize, tool, {"id": 3, "method": "ping"}]))
        ),
    )
    markdownify.client(tmp_path)
    output = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert output[1]["id"] == 2
    assert "not replayed" in output[1]["error"]["message"]
    assert sum(body == tool for _, body, _ in calls) == 1
    assert (
        "POST",
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        "new",
    ) in calls
    assert ("POST", {"id": 3, "method": "ping"}, "new") in calls
    assert calls[-1] == ("DELETE", None, "new")


@pytest.mark.parametrize(
    "status, error", [(404, markdownify._SessionExpired), (401, PermissionError)]
)
def test_only_session_404_has_a_reinitialization_signal(monkeypatch, status, error):
    monkeypatch.setattr(
        markdownify,
        "core",
        SimpleNamespace(
            STATE=markdownify.Path("fixture-state"),
            read_json=lambda _: {"owner_pid": 77, "owner_birth": 1},
            process_birth=lambda _: 1,
            credential=lambda: "fixture-token",
        ),
    )
    row = SimpleNamespace(
        status="ESTABLISHED",
        laddr=SimpleNamespace(ip="127.0.0.1", port=88),
        raddr=SimpleNamespace(port=99),
        pid=77,
    )
    monkeypatch.setattr(
        markdownify, "psutil", SimpleNamespace(net_connections=lambda **_: [row])
    )
    connection = Mock()
    connection.sock.getsockname.return_value = ("127.0.0.1", 99)
    response = connection.getresponse.return_value
    response.status = status
    response.read.return_value = b""
    monkeypatch.setattr(
        markdownify.http.client, "HTTPConnection", lambda *_, **__: connection
    )
    with pytest.raises(error) as raised:
        markdownify.request({"port": 88}, "POST", "/mcp", {"id": 2}, "expired")
    assert type(raised.value) is error
    connection.close.assert_called_once()


def test_completed_body_cancels_deadline_before_conversion(handler):
    handler.server = Mock(spec=markdownify._BoundedHTTPServer)
    handler.connection = Mock()
    handler._finish_reading()
    handler.server.finish_reading.assert_called_once_with(
        handler.connection, completed=True
    )


def test_expired_session_without_initialization_cannot_recover_or_replay(monkeypatch):
    request = Mock(side_effect=markdownify._SessionExpired("expired"))
    monkeypatch.setattr(markdownify, "request", request)
    with pytest.raises(markdownify._SessionExpired):
        markdownify._forward_request({}, {"id": 1, "method": "tools/call"}, "old", None)
    request.assert_called_once()


def test_client_decodes_utf8_protocol_bytes_despite_windows_text_encoding(
    tmp_path, monkeypatch
):
    value = {
        "id": 1,
        "method": "tools/call",
        "params": {"arguments": {"filepath": "данные.md"}},
    }
    raw = (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")
    stream = TextIOWrapper(BytesIO(raw), encoding="cp1251")
    monkeypatch.setattr(markdownify.sys, "stdin", stream)
    monkeypatch.setattr(markdownify, "specification", lambda _: {})
    seen = []

    def request(spec, method, path, body=None, session=None):
        if method == "GET":
            return {"ready": True}, None
        seen.append(body)
        return {"id": 1, "result": {}}, None

    monkeypatch.setattr(markdownify, "request", request)
    markdownify.client(tmp_path)
    assert seen == [value]


def test_client_refuses_non_utf8_bytes_before_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(
        markdownify.sys, "stdin", TextIOWrapper(BytesIO(b"\xff\n"), encoding="cp1251")
    )
    monkeypatch.setattr(markdownify, "specification", lambda _: {})
    request = Mock(return_value=({"ready": True}, None))
    monkeypatch.setattr(markdownify, "request", request)
    with pytest.raises(UnicodeDecodeError):
        markdownify.client(tmp_path)
    request.assert_called_once_with({}, "GET", markdownify.HEALTH_PATH)


def test_stop_marker_is_published_under_the_generation_transition_lock(
    tmp_path, monkeypatch
):
    held = []

    class Transition:
        def __enter__(self):
            held.append(True)

        def __exit__(self, *_):
            held.pop()

    def read(_):
        assert held
        return {"owner_pid": 77, "owner_birth": 1, "generation": "current"}

    def write(_, value):
        assert held
        assert value == {"generation": "current"}

    monkeypatch.setattr(markdownify, "specification", lambda _: {})
    monkeypatch.setattr(
        markdownify,
        "core",
        SimpleNamespace(
            STATE=tmp_path,
            LifetimeLock=lambda _: Transition(),
            read_json=read,
            write_json=write,
            process_birth=lambda _: 1,
        ),
    )
    monkeypatch.setattr(
        markdownify, "psutil", SimpleNamespace(pid_exists=lambda _: False)
    )
    markdownify._stop(tmp_path)
    assert not held


def test_stdio_decodes_native_windows_bytes_as_utf8_even_with_cp1251_wrapper():
    from io import TextIOWrapper

    request = {
        "id": 1,
        "method": "tools/call",
        "params": {"name": "get-markdown-file", "arguments": {"filepath": "данные.md"}},
    }
    wire = json.dumps(request, ensure_ascii=False).encode("utf-8") + b"\n"
    with TextIOWrapper(BytesIO(wire), encoding="cp1251") as redirected:
        assert list(markdownify._stdio_requests(redirected)) == [request]


def test_stdio_size_limit_counts_utf8_bytes_and_rejects_invalid_utf8():
    with pytest.raises(ValueError, match="Oversized"):
        list(markdownify._stdio_requests(StringIO("я" * (600 * 1024))))
    with pytest.raises(UnicodeDecodeError):
        list(markdownify._stdio_requests(BytesIO(b'"\xff"\n')))
