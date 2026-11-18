"""A private protocol connection cannot create a persistent service owner."""

from email.message import Message
from io import BytesIO, StringIO
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
        sessions=set(),
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
    assert handler._sessions == {session}
    handler.headers["Mcp-Session-Id"] = session
    handler._dispatch_request({"id": 2, "method": "tools/list"})
    assert [
        tool["name"] for tool in handler.reply.call_args.args[1]["result"]["tools"]
    ] == ["get-markdown-file"]
    handler.do_DELETE()
    assert not handler._sessions
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
    handler._sessions.update(str(i) for i in range(64))
    handler._dispatch_request({"id": 1, "method": "initialize"})
    handler.reply.assert_called_with(503)
    handler.headers["Mcp-Session-Id"] = "0"
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
