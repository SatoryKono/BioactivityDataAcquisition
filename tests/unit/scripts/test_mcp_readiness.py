"""Protocol, semantic, isolation-reason and redaction readiness regressions."""

from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
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
        tmp_path, {"config": {"mcp_servers": {"filesystem": entry}}, "origins": {}}
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
                "serverInfo": {"name": "filesystem"},
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
        expected=["filesystem"],
        required=["filesystem"],
        profile="stable",
        controls={"filesystem": control} if control is not None else {},
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
        (capture(tmp_path, tool_timeout_sec=None), {"filesystem": CONTROL}),
    ):
        result = readiness_report(
            value,
            expected=["filesystem"],
            required=["filesystem"],
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
        expected=["filesystem", "missing"],
        required=["filesystem", "missing"],
        profile="stable",
        controls={},
        environment={},
    )
    assert {row["server"]: row["status"] for row in result["results"]} == {
        "filesystem": "DISABLED",
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
    after.payload["config"]["mcp_servers"]["filesystem"]["env"]["TOKEN"] = "rotated"
    value = report(before, Session(), after=lambda: after)
    assert value["results"][0]["status"] == "STALE"
    assert value["status"] == "STALE"

    def unavailable():
        raise RuntimeError(SECRET)

    value = report(before, Session(), after=unavailable)
    assert value["results"][0]["status"] == "STALE"
    assert value["status"] == "STALE"
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
        expected=["filesystem"],
        required=["filesystem"],
        profile="stable",
        controls={"filesystem": CONTROL},
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
                    "serverInfo": {"name": "filesystem"},
                },
                "tools/list": {"tools": [{"name": "read_file"}]},
                "tools/call": {"content": [{"type": "text", "text": SECRET}]},
            }[payload["method"]]
            raw = json.dumps(
                {"jsonrpc": "2.0", "id": payload["id"], "result": result}
            ).encode()
            if self.path in {"/slow-json", "/slow-sse", "/slow-headers"}:
                import time

                if self.path == "/slow-sse":
                    raw = b"data: " + raw + b"\n\n"
                try:
                    if self.path == "/slow-headers":
                        self.wfile.write(b"HTTP/1.0 200 OK\r\n")
                        raw = b"Content-Type: application/json\r\n\r\n" + raw
                    else:
                        self.send_response(200)
                        self.send_header(
                            "Content-Type",
                            "text/event-stream"
                            if self.path == "/slow-sse"
                            else "application/json",
                        )
                        self.send_header("Content-Length", str(len(raw)))
                        self.end_headers()
                    for byte in raw:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(0.02)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
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
                    "filesystem": {
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
        expected=["filesystem"],
        required=["filesystem"],
        profile="stable",
        controls={"filesystem": CONTROL},
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
                    "filesystem": {
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
        expected=["filesystem"],
        required=["filesystem"],
        profile="stable",
        controls={
            "filesystem": {
                **CONTROL,
                "expected_policy_reason": "WORKSPACE_POLICY_DENIED",
            }
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


def test_unknown_valid_protocol_is_client_not_tested_not_server_failure(tmp_path):
    session = Session(
        {
            "initialize": {
                "protocolVersion": "2099-01-01",
                "capabilities": {},
                "serverInfo": {"name": "future-fixture"},
            }
        }
    )
    result = report(capture(tmp_path), session)
    assert result["status"] == "NOT_TESTED"
    assert result["results"][0]["detail"] == "PROTOCOL_VERSION_NOT_SUPPORTED"
    assert not any(method == "tools/call" for method, _, _ in session.calls)


def test_deja_fix_is_not_an_approved_filesystem_operation(tmp_path):
    session = Session()
    result = report(capture(tmp_path), session, control={**CONTROL, "tool": "fix"})
    assert result["results"][0]["status"] == "NOT_TESTED"
    assert result["results"][0]["detail"] == "READ_CONTROL_NOT_APPROVED"
    assert session.calls == []


def test_legacy_timeout_flags_are_rejected_before_any_mcp_call(monkeypatch, capsys):
    from scripts.ai.codex import doctor

    monkeypatch.setattr(sys, "argv", ["doctor.py", "mcp", "--timeout", "1"])
    monkeypatch.setattr(
        doctor, "run_mcp", lambda *args, **kwargs: pytest.fail("unexpected MCP call")
    )
    with pytest.raises(SystemExit) as error:
        doctor.main()
    assert error.value.code == 2
    assert "native route limits" in capsys.readouterr().err


@pytest.mark.parametrize(
    "script,category",
    [
        ("mcp_memory_wrapper.ps1", "ADAPTER_DISABLED_BY_POLICY"),
        ("unrelated.py", "TRANSPORT_ERROR"),
    ],
)
def test_exit_78_means_disabled_only_for_the_project_memory_wrapper(
    tmp_path, monkeypatch, script, category
):
    from types import SimpleNamespace
    from scripts.ai.codex.mcp_probe_client import StdioProbeClient
    from scripts.ai.codex.native_mcp_config import NativeConfigError

    client = StdioProbeClient(
        {"command": sys.executable, "args": [str(tmp_path / script)]}, tmp_path, {}
    )
    client._process = SimpleNamespace(poll=lambda: 78)
    monkeypatch.setattr(client, "_send", lambda *args: None)

    def closed(*args):
        raise NativeConfigError("native config process closed before responding")

    monkeypatch.setattr(client, "_response", closed)
    with pytest.raises(ProbeError) as error:
        client.request("initialize", {}, 90)
    assert error.value.category == category


def test_probe_plan_is_bounded_and_confined(tmp_path):
    from scripts.ai.codex.doctor import _read_probe_plan

    control_root = tmp_path / "reports/quality/mcp-controls"
    control_root.mkdir(parents=True)
    plan = control_root / "control.json"
    plan.write_text('{"filesystem": {}}', encoding="utf-8")
    assert _read_probe_plan(tmp_path, plan.relative_to(tmp_path)) == {"filesystem": {}}
    for requested in (
        plan,
        Path("../control.json"),
        Path("reports/quality/outside.json"),
    ):
        with pytest.raises((ValueError, FileNotFoundError)):
            _read_probe_plan(tmp_path, requested)
    plan.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match="size limit"):
        _read_probe_plan(tmp_path, plan.relative_to(tmp_path))


def test_probe_plan_rejects_symlink_escape(tmp_path):
    from scripts.ai.codex.doctor import _read_probe_plan

    control_root = tmp_path / "reports/quality/mcp-controls"
    control_root.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    linked = control_root / "control.json"
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(ValueError, match="mcp-controls"):
        _read_probe_plan(tmp_path, linked.relative_to(tmp_path))


@pytest.mark.parametrize("cwd_relative", [False, True])
def test_stdio_respects_effective_cwd_and_relative_script(tmp_path, cwd_relative):
    directory = tmp_path / "adapter-cwd"
    directory.mkdir()
    adapter = directory / "cwd_adapter.py"
    adapter.write_text(
        """import json,os,sys
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r: continue
 m=r['method']
 v={'protocolVersion':'2025-03-26','capabilities':{},'serverInfo':{'name':'fixture'}} if m=='initialize' else {'tools':[{'name':'read_file'}]} if m=='tools/list' else {'content':[{'type':'text','text':os.getcwd()}]}
 print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':v}),flush=True)
""",
        encoding="utf-8",
    )
    value = capture(
        tmp_path,
        command=sys.executable,
        args=["-u", adapter.name],
        cwd=directory.name if cwd_relative else str(directory),
    )
    result = readiness_report(
        value,
        expected=["filesystem"],
        required=["filesystem"],
        profile="stable",
        controls={"filesystem": {**CONTROL, "contains_all": [str(directory)]}},
        environment={},
    )
    assert result["results"][0]["phases"]["tool"]["status"] == "PASS"


@pytest.mark.parametrize("mode", ["off", "read-only"])
def test_task_memory_restriction_survives_environment_filter(monkeypatch, mode):
    from scripts.ai.codex.mcp_probe_client import probe_environment

    monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", mode)
    monkeypatch.setenv("UNRELATED_SECRET", SECRET)
    result = probe_environment(
        {"env": {"BIOETL_AI_MEMORY_MODE": "read-write"}},
        {"BIOETL_AI_MEMORY_MODE": "read-write"},
    )
    assert result["BIOETL_AI_MEMORY_MODE"] == mode
    assert "UNRELATED_SECRET" not in result


@pytest.mark.parametrize("method", ["initialize", "tools/list"])
def test_early_policy_denial_does_not_pass_control(tmp_path, method):
    session = Session({method: ProbeError("WORKSPACE_POLICY_DENIED")})
    result = report(
        capture(tmp_path),
        session,
        control={**CONTROL, "expected_policy_reason": "WORKSPACE_POLICY_DENIED"},
    )
    row = result["results"][0]
    assert row["status"] == "FAIL"
    assert row["control_status"] == "NOT_TESTED"
    assert not any(call[0] == "tools/call" for call in session.calls)


@pytest.mark.parametrize(
    "name",
    ["mcp_context7_wrapper.sh", "mcp_ast_grep_wrapper.sh", "mcp_deja_wrapper.ps1"],
)
def test_existing_legacy_wrapper_does_not_prove_no_install_backend(tmp_path, name):
    from scripts.ai.codex.mcp_probe_client import client_for

    adapter = tmp_path / name
    adapter.write_text("# fallback may install a package", encoding="utf-8")
    launcher = "powershell" if adapter.suffix == ".ps1" else "bash"
    args = (
        ["-NoProfile", "-File", str(adapter)]
        if launcher == "powershell"
        else [str(adapter)]
    )
    with pytest.raises(ProbeError, match="WRAPPER_BACKEND_NO_INSTALL_NOT_VERIFIED"):
        client_for({"command": launcher, "args": args}, tmp_path, {})


@pytest.mark.parametrize("suffix", ["/slow-json", "/slow-sse", "/slow-headers"])
def test_http_slow_drip_obeys_total_deadline_without_replay(http_mcp_fixture, suffix):
    import time
    from scripts.ai.codex.mcp_http_probe import HttpProbeClient

    url, seen = http_mcp_fixture
    started = time.monotonic()
    with HttpProbeClient({"url": url + suffix}, None, {}) as client:
        with pytest.raises(ProbeError) as error:
            client.request("tools/list", {}, 0.1)
    elapsed = time.monotonic() - started
    assert error.value.uncertain
    assert elapsed < 0.6, f"request exceeded its total observation budget: {elapsed}"
    assert len(seen) == 1
