"""Protocol, semantic, isolation-reason and redaction readiness regressions."""

from copy import deepcopy
from io import BytesIO
import json
import sys

import pytest

from scripts.ai.codex.mcp_probe_client import (
    ProbeError,
    _read_http_reply,
    rpc_result,
)
from scripts.ai.codex.mcp_readiness import readiness_report
from scripts.ai.codex.native_mcp_config import ConfigCapture

pytestmark = pytest.mark.unit
SECRET = "private-control-marker-not-for-logs"


def capture(tmp_path, **updates):
    entry = {
        "command": "python",
        "args": [],
        "startup_timeout_sec": 90,
        "tool_timeout_sec": 120,
    }
    entry.update(updates)
    return ConfigCapture(
        tmp_path, {"config": {"mcp_servers": {"fixture": entry}}, "origins": {}}
    )


CONTROL = {
    "tool": "read_file",
    "arguments": {"path": "README.md"},
    "contains_all": [SECRET],
}


class Session:
    def __init__(self, overrides=None):
        self.calls = []
        self.closed = False
        self.transport_seen = False
        self.overrides = overrides or {}

    def request(self, method, params, timeout):
        self.calls.append((method, params, timeout))
        self.transport_seen = True
        value = self.overrides.get(method)
        if isinstance(value, Exception):
            raise value
        if value is not None:
            return value
        return {
            "initialize": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "serverInfo": {"name": "fixture"},
            },
            "tools/list": {"tools": [{"name": "read_file"}]},
            "tools/call": {"content": [{"type": "text", "text": SECRET}]},
        }[method]

    def notify_initialized(self):
        self.calls.append(("notifications/initialized", {}, None))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True


def report(value, session, *, control=CONTROL, after=None):
    return readiness_report(
        value,
        expected=["fixture"],
        required=["fixture"],
        profile="stable",
        controls={"fixture": control} if control is not None else {},
        environment={},
        after=after,
        factory=lambda *args: session,
    )


def test_tool_success_does_not_invent_backend_or_ordinary_session_acceptance(tmp_path):
    session = Session()
    value = report(capture(tmp_path), session)
    row = value["results"][0]
    assert row["phases"]["tool"]["status"] == "PASS"
    assert row["phases"]["transport"]["status"] == "PASS"
    assert row["backend_identity_status"] == "NOT_TESTED"
    assert row["status"] == "NOT_TESTED" and not value["ready"]
    assert value["ordinary_user_session"] == "NOT_TESTED"
    assert SECRET not in json.dumps(value)
    assert session.closed


@pytest.mark.parametrize(
    "overrides,reason",
    [
        (
            {"initialize": {"protocolVersion": "broken", "capabilities": {}}},
            "INITIALIZE_CONTRACT",
        ),
        ({"tools/list": {"tools": []}}, "CONTROL_TOOL_MISSING"),
        ({"tools/call": {"content": []}}, "EMPTY_TOOL_RESULT"),
        (
            {"tools/call": {"content": [{"type": "text", "text": ""}]}},
            "EMPTY_TOOL_RESULT",
        ),
        (
            {"tools/call": {"content": [{"type": "text", "text": "unrelated"}]}},
            "CONTROL_RESULT_MISMATCH",
        ),
        (
            {
                "tools/call": {
                    "isError": True,
                    "content": [{"type": "text", "text": SECRET}],
                }
            },
            "TOOL_REPORTED_ERROR",
        ),
    ],
)
def test_transport_and_empty_success_never_prove_readiness(tmp_path, overrides, reason):
    session = Session(overrides)
    value = report(capture(tmp_path), session)
    assert value["status"] == "FAIL"
    assert value["results"][0]["detail"] == reason
    assert not value["ready"] and session.closed
    assert SECRET not in json.dumps(value)


@pytest.mark.parametrize(
    "category,status",
    [("AUTH_ERROR", "FAIL"), ("WORKSPACE_POLICY_DENIED", "DENIED_AS_EXPECTED")],
)
def test_expected_denial_requires_typed_policy_reason(tmp_path, category, status):
    session = Session({"tools/call": ProbeError(category)})
    control = {**CONTROL, "expected_policy_reason": "WORKSPACE_POLICY_DENIED"}
    value = report(capture(tmp_path), session, control=control)
    assert value["results"][0]["status"] == status
    assert not value["ready"]


def test_timeout_is_uncertain_and_call_is_never_replayed(tmp_path):
    session = Session({"tools/call": ProbeError("TIMEOUT", uncertain=True)})
    row = report(capture(tmp_path), session)["results"][0]
    assert row["uncertain_outcome"] is True
    assert [method for method, _, _ in session.calls].count("tools/call") == 1
    assert session.closed


def test_missing_limit_or_control_never_starts_an_adapter(tmp_path):
    def forbidden(*_):
        pytest.fail("must not launch an adapter without a bounded declared control")

    for value, controls in (
        (capture(tmp_path), {}),
        (capture(tmp_path, tool_timeout_sec=None), {"fixture": CONTROL}),
    ):
        result = readiness_report(
            value,
            expected=["fixture"],
            required=["fixture"],
            profile="stable",
            controls=controls,
            environment={},
            factory=forbidden,
        )
        assert result["results"][0]["status"] == "NOT_TESTED"


def test_disabled_and_absent_routes_are_explicit(tmp_path):
    value = capture(tmp_path, enabled=False)
    result = readiness_report(
        value,
        expected=["fixture", "missing"],
        required=["fixture", "missing"],
        profile="stable",
        controls={},
        environment={},
    )
    assert {row["server"]: row["status"] for row in result["results"]} == {
        "fixture": "DISABLED",
        "missing": "FAIL",
    }
    assert result["status"] == "FAIL"


def test_paginated_catalog_is_read_before_control_call(tmp_path):
    class Paginated(Session):
        def request(self, method, params, timeout):
            if method == "tools/list":
                self.calls.append((method, params, timeout))
                return (
                    {"tools": [{"name": "read_file"}]}
                    if params
                    else {"tools": [], "nextCursor": "next"}
                )
            return super().request(method, params, timeout)

    session = Paginated()
    row = report(capture(tmp_path), session)["results"][0]
    assert row["phases"]["catalog"]["status"] == "PASS"
    assert [args for method, args, _ in session.calls if method == "tools/list"] == [
        {},
        {"cursor": "next"},
    ]


def test_private_rotation_and_final_capture_failure_invalidate_results(tmp_path):
    before = capture(tmp_path, env={"TOKEN": SECRET})
    after = ConfigCapture(tmp_path, deepcopy(before.payload))
    after.payload["config"]["mcp_servers"]["fixture"]["env"]["TOKEN"] = "rotated"
    value = report(before, Session(), after=lambda: after)
    assert value["results"][0]["status"] == "STALE"

    def unavailable():
        raise RuntimeError(SECRET)

    value = report(before, Session(), after=unavailable)
    assert value["results"][0]["status"] == "STALE"
    assert SECRET not in json.dumps(value)


def test_memory_read_graph_and_mutations_are_not_diagnostic_controls(tmp_path):
    for name in ("read_graph", "create_entities", "delete_entities", "remember"):
        row = report(capture(tmp_path), Session(), control={**CONTROL, "tool": name})[
            "results"
        ][0]
        assert row["detail"] == "READ_CONTROL_NOT_APPROVED"


def test_stdio_real_exchange_is_bounded_closed_and_has_no_payload_log(tmp_path):
    script = """import sys,json
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r: continue
 m=r['method']
 value={'protocolVersion':'2025-03-26','capabilities':{},'serverInfo':{'name':'fixture'}} if m=='initialize' else {'tools':[{'name':'read_file'}]} if m=='tools/list' else {'content':[{'type':'text','text':'private-control-marker-not-for-logs'}]}
 print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':value}),flush=True)
"""
    adapter = tmp_path / "fixture_adapter.py"
    adapter.write_text(script, encoding="utf-8")
    value = capture(tmp_path, command=sys.executable, args=["-u", str(adapter)])
    result = readiness_report(
        value,
        expected=["fixture"],
        required=["fixture"],
        profile="stable",
        controls={"fixture": CONTROL},
        environment={},
    )
    assert result["results"][0]["phases"]["tool"]["status"] == "PASS"
    assert SECRET not in json.dumps(result)


def test_streamable_sse_ignores_notification_and_preserves_response():
    response = BytesIO(
        b'data: {"method":"notifications/message"}\n\ndata: {"id":7,"result":{"ok":true}}\n\n'
    )
    response.headers = {"Content-Type": "text/event-stream"}
    assert (
        json.loads(_read_http_reply(response, 1).decode().split("data: ", 1)[1])["id"]
        == 7
    )


def test_rpc_errors_never_disclose_server_messages():
    with pytest.raises(ProbeError, match="RPC_ERROR") as error:
        rpc_result({"error": {"code": -1, "message": SECRET}})
    assert SECRET not in str(error.value)


@pytest.fixture
def http_mcp_fixture():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    observations = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            return None

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            observations.append(
                (
                    self.path,
                    payload.get("method"),
                    self.headers.get("Mcp-Session-Id"),
                    self.headers.get("Authorization"),
                )
            )
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/target")
                self.end_headers()
                return
            if self.path == "/denied":
                self.send_response(403)
                self.end_headers()
                return
            if "id" not in payload:
                self.send_response(202)
                self.end_headers()
                return
            result = {
                "initialize": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "serverInfo": {"name": "fixture"},
                },
                "tools/list": {"tools": [{"name": "read_file"}]},
                "tools/call": {"content": [{"type": "text", "text": SECRET}]},
            }[payload["method"]]
            raw = json.dumps(
                {"jsonrpc": "2.0", "id": payload["id"], "result": result}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Mcp-Session-Id", "fixture-session")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", observations
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_exchange_keeps_session_auth_and_payloads_private(
    tmp_path, http_mcp_fixture
):
    url, seen = http_mcp_fixture
    value = ConfigCapture(
        tmp_path,
        {
            "config": {
                "mcp_servers": {
                    "fixture": {
                        "url": url,
                        "startup_timeout_sec": 5,
                        "tool_timeout_sec": 5,
                        "bearer_token_env_var": "FIXTURE_TOKEN",
                    }
                }
            },
            "origins": {},
        },
    )
    result = readiness_report(
        value,
        expected=["fixture"],
        required=["fixture"],
        profile="stable",
        controls={"fixture": CONTROL},
        environment={"FIXTURE_TOKEN": SECRET},
    )
    assert result["results"][0]["phases"]["tool"]["status"] == "PASS"
    assert seen[0][2] is None
    assert all(row[2] == "fixture-session" for row in seen[1:])
    assert all(row[3] == "Bearer " + SECRET for row in seen)
    assert SECRET not in json.dumps(result)


@pytest.mark.parametrize(
    "suffix,reason", [("/redirect", "HTTP_ERROR"), ("/denied", "AUTH_ERROR")]
)
def test_http_never_follows_redirect_or_calls_auth_failure_policy_success(
    tmp_path, http_mcp_fixture, suffix, reason
):
    url, seen = http_mcp_fixture
    value = ConfigCapture(
        tmp_path,
        {
            "config": {
                "mcp_servers": {
                    "fixture": {
                        "url": url + suffix,
                        "startup_timeout_sec": 5,
                        "tool_timeout_sec": 5,
                    }
                }
            },
            "origins": {},
        },
    )
    result = readiness_report(
        value,
        expected=["fixture"],
        required=["fixture"],
        profile="stable",
        controls={
            "fixture": {**CONTROL, "expected_policy_reason": "WORKSPACE_POLICY_DENIED"}
        },
        environment={},
    )
    assert result["results"][0]["status"] == "FAIL"
    assert result["results"][0]["detail"] == reason
    assert len(seen) == 1 and seen[0][0] == suffix


@pytest.mark.parametrize(
    "command,args",
    [
        ("npx", ["-y", "new-package"]),
        ("docker", ["run", "unreviewed-image"]),
        ("python", ["-cprint('secret')"]),
        ("python", ["-m", "pip", "install", "new-package"]),
        ("node", ["--print", "arbitrary_code"]),
    ],
)
def test_installers_and_inline_prefixes_are_not_started(tmp_path, command, args):
    from scripts.ai.codex.mcp_probe_client import client_for

    adapter = tmp_path / "existing.py"
    adapter.write_text("raise AssertionError('must not run')", encoding="utf-8")
    with pytest.raises(ProbeError, match="NOT_TESTED"):
        client_for({"command": command, "args": [*args, str(adapter)]}, tmp_path, {})


def test_supported_older_protocol_is_negotiated_without_false_failure(tmp_path):
    session = Session(
        {
            "initialize": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "legacy-compatible"},
            }
        }
    )
    row = report(capture(tmp_path), session)["results"][0]
    assert row["phases"]["initialize"]["status"] == "PASS"
    assert row["phases"]["tool"]["status"] == "PASS"
