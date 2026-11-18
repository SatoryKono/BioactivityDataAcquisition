"""A private protocol connection cannot create a persistent service owner."""

from email.message import Message
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, StringIO
import json
from threading import Event, Lock
from unittest.mock import Mock

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
