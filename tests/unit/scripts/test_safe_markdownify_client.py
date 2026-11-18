"""A private protocol connection cannot create a persistent service owner."""

from email.message import Message
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, StringIO
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
    server.shutdown_request = Mock()
    start = Mock()
    monkeypatch.setattr(markdownify.ThreadingHTTPServer, "process_request", start)
    server.process_request("first", None)
    server.process_request("second", None)
    server.process_request("excess", None)
    assert start.call_count == 2
    server.shutdown_request.assert_called_once_with("excess")
    worker = Mock(side_effect=RuntimeError("handler failure"))
    monkeypatch.setattr(
        markdownify.ThreadingHTTPServer, "process_request_thread", worker
    )
    with pytest.raises(RuntimeError, match="handler failure"):
        server.process_request_thread("first", None)
    server.process_request("replacement", None)
    assert start.call_count == 3


def test_failed_thread_start_releases_connection_capacity(monkeypatch):
    server = object.__new__(markdownify._BoundedHTTPServer)
    server._slots = markdownify.threading.BoundedSemaphore(1)
    monkeypatch.setattr(
        markdownify.ThreadingHTTPServer,
        "process_request",
        Mock(side_effect=RuntimeError("cannot start thread")),
    )
    with pytest.raises(RuntimeError, match="cannot start thread"):
        server.process_request(None, None)
    assert server._slots.acquire(blocking=False)


def test_header_deadline_closes_slow_connection_and_is_cancelled(handler, monkeypatch):
    timer = Mock()
    callbacks = []

    def create_timer(seconds, callback):
        assert seconds == markdownify.HTTP_HEADER_SECONDS
        callbacks.append(callback)
        return timer

    handler.connection = Mock()
    monkeypatch.setattr(markdownify.threading, "Timer", create_timer)
    monkeypatch.setattr(
        markdownify.BaseHTTPRequestHandler,
        "handle_one_request",
        lambda self: callbacks[0](),
    )
    handler.handle_one_request()
    handler.connection.shutdown.assert_called_once_with(markdownify.socket.SHUT_RDWR)
    timer.start.assert_called_once()
    timer.cancel.assert_called_once()
    assert handler.authorized() is False


def test_foreign_stop_marker_does_not_disable_current_generation_watcher(
    tmp_path, monkeypatch
):
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


def test_completed_headers_cancel_deadline_before_conversion(handler):
    handler._header_expired = Event()
    handler._header_timer = Mock()
    assert handler.authorized() is True
    handler._header_timer.cancel.assert_called_once()


def test_expired_session_without_initialization_cannot_recover_or_replay(monkeypatch):
    request = Mock(side_effect=markdownify._SessionExpired("expired"))
    monkeypatch.setattr(markdownify, "request", request)
    with pytest.raises(markdownify._SessionExpired):
        markdownify._forward_request({}, {"id": 1, "method": "tools/call"}, "old", None)
    request.assert_called_once()


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
