"""A private protocol connection cannot create a persistent service owner."""

from io import StringIO

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
    monkeypatch.setattr(markdownify, "ensure", lambda *_: pytest.fail("client started a persistent owner"))
    markdownify.client(tmp_path)
    assert calls == [("GET", "/health")]


def test_unready_owner_does_not_trigger_an_implicit_start(tmp_path, monkeypatch):
    monkeypatch.setattr(markdownify, "specification", lambda root: {"root": root})
    monkeypatch.setattr(markdownify, "request", lambda *_: ({"ready": False}, None))
    monkeypatch.setattr(markdownify, "ensure", lambda *_: pytest.fail("client started a persistent owner"))
    with pytest.raises(PermissionError, match="administrative"):
        markdownify.client(tmp_path)
