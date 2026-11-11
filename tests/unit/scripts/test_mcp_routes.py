"""Native authority, secret minimization, drift and diagnostic-process contracts."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

pytestmark = pytest.mark.unit

from scripts.ai.codex import doctor
from scripts.ai.codex.mcp_routes import (
    changed_routes,
    route_snapshot,
    transport_projection,
)
from scripts.ai.codex.native_mcp_config import (
    ConfigCapture,
    NativeConfigClient,
    NativeConfigError,
)

SECRET = "do-not-log-this-credential"
USER = {"type": "user", "file": "/user/config.toml"}
PROJECT = {"type": "project", "dotCodexFolder": "/project/.codex"}


def capture(tmp_path: Path) -> ConfigCapture:
    entry = {
        "command": "python",
        "args": ["-I", "/project/adapter.py", "--profile", "graph-a"],
        "env": {"GITHUB_TOKEN": SECRET, "GITHUB_TOOLSETS": "repos"},
        "startup_timeout_sec": 90,
        "tool_timeout_sec": 120,
    }
    payload = {
        "config": {"mcp_servers": {"github": entry}},
        "origins": {"mcp_servers.github.command": {"name": USER, "version": SECRET}},
        "layers": [
            {
                "name": USER,
                "version": SECRET,
                "config": {"mcp_servers": {"github": deepcopy(entry)}},
            }
        ],
    }
    return ConfigCapture(tmp_path, payload)


def snapshot(value: ConfigCapture, **kwargs: object) -> dict[str, object]:
    return route_snapshot(
        value, expected=["github", "memory"], project_profile="stable", **kwargs
    )


def test_native_effective_value_wins_without_remerging_layers(tmp_path: Path) -> None:
    value = capture(tmp_path)
    value.payload["layers"].insert(
        0,
        {
            "name": PROJECT,
            "version": "ignored",
            "config": {"mcp_servers": {"github": {"command": "node"}}},
        },
    )
    value.payload["origins"]["mcp_servers.github.command"] = {
        "name": PROJECT,
        "version": SECRET,
    }
    result = snapshot(value)
    selection = result["routes"]["github"]["selection"]
    assert selection["transport"]["command"] == "python"
    assert selection["origins"]["command"] == PROJECT
    assert [item["source"] for item in selection["declarations"]] == [PROJECT, USER]
    assert result["missing"] == ["memory"]
    assert result["session_tool_readiness"] == "NOT_TESTED"


def test_no_credential_value_or_secret_revision_hash_is_published(
    tmp_path: Path,
) -> None:
    value = capture(tmp_path)
    value.payload["layers"][0]["disabledReason"] = SECRET
    rendered = json.dumps(snapshot(value))
    assert SECRET not in rendered
    assert SECRET not in repr(value)
    assert hashlib.sha256(SECRET.encode()).hexdigest() not in rendered
    assert "GITHUB_TOKEN" in rendered
    assert "native layer disabled" in rendered
    assert value.revisions() == (SECRET,)


def test_instance_recovery_does_not_change_selection_fingerprint(
    tmp_path: Path,
) -> None:
    value = capture(tmp_path)
    before = snapshot(value, instances={"github": {"generation": "one", "pid": 1}})
    after = snapshot(value, instances={"github": {"generation": "two", "pid": 2}})
    first, second = before["routes"]["github"], after["routes"]["github"]
    assert first["selection_fingerprint"] == second["selection_fingerprint"]
    assert first["runtime_instance"] != second["runtime_instance"]
    assert second["backend_identity_verified"] is False


def test_private_auth_rotation_marks_only_affected_route_stale(tmp_path: Path) -> None:
    before = capture(tmp_path)
    before.payload["config"]["mcp_servers"]["other"] = {"command": "node", "args": []}
    after = ConfigCapture(tmp_path, deepcopy(before.payload))
    after.payload["config"]["mcp_servers"]["github"]["env"]["GITHUB_TOKEN"] = (
        "rotated-private-value"
    )
    assert changed_routes(before, after) == ["github"]
    assert (
        snapshot(before)["routes"]["github"]["selection_fingerprint"]
        == snapshot(after)["routes"]["github"]["selection_fingerprint"]
    )


def test_same_binary_with_different_auth_profiles_is_not_deduplicated(
    tmp_path: Path,
) -> None:
    value = capture(tmp_path)
    servers = value.payload["config"]["mcp_servers"]
    servers["github-second"] = deepcopy(servers["github"])
    result = snapshot(
        value, auth_references={"github": "authority-a", "github-second": "authority-b"}
    )
    assert result["effective"] == ["github", "github-second"]
    assert (
        result["routes"]["github"]["selection_fingerprint"]
        != result["routes"]["github-second"]["selection_fingerprint"]
    )


@pytest.mark.parametrize(
    "entry",
    [
        {"command": "python", "args": ["--token", SECRET]},
        {"command": "python", "args": ["--token=" + SECRET]},
        {"command": "node", "args": ["-e", SECRET]},
        {"command": "python", "args": ["-cprint('" + SECRET + "')"]},
        {"command": "node", "args": ["-econsole.log('" + SECRET + "')"]},
        {"command": "python", "args": ["--" + SECRET]},
        {"command": "node", "args": ["-DNAME=" + SECRET]},
        {"command": "python", "args": [SECRET]},
        {"url": "https://user:" + SECRET + "@example.org/mcp?key=" + SECRET},
        {"url": "https://example.org/" + SECRET},
        {"url": "https://example.org/mcp", "http_headers": {"Authorization": SECRET}},
    ],
)
def test_inline_credentials_and_opaque_arguments_are_omitted(
    entry: dict[str, object],
) -> None:
    public, complete = transport_projection(entry)
    assert SECRET not in json.dumps(public)
    assert complete is False


def test_env_header_reference_survives_without_its_value() -> None:
    public, complete = transport_projection(
        {
            "url": "https://api.example.org/mcp",
            "env_http_headers": {"Authorization": "MCP_TOKEN"},
        }
    )
    assert public["auth_env_references"] == {"Authorization": "MCP_TOKEN"}
    assert complete is True


def test_effective_disable_and_workspace_drift_are_explicit(tmp_path: Path) -> None:
    value = capture(tmp_path)
    value.payload["config"]["mcp_servers"]["github"]["enabled"] = False
    assert snapshot(value)["disabled"] == ["github"]
    assert changed_routes(value, ConfigCapture(tmp_path / "other", value.payload)) == [
        "github"
    ]


def server_command(tmp_path: Path, reply: str) -> list[str]:
    script = (
        "import json,sys,time\nfrom pathlib import Path\nfor line in sys.stdin:\n request=json.loads(line)\n with Path(sys.argv[1]).open('a',encoding='utf-8') as log: log.write(json.dumps(request)+'\\n')\n "
        + reply.replace("\n", "\n ")
    )
    return [sys.executable, "-u", "-c", script, str(tmp_path / "requests.jsonl")]


def test_native_exchange_only_reads_config_and_closes_owned_process(
    tmp_path: Path,
) -> None:
    payload = {"config": {"mcp_servers": {}}, "origins": {}, "layers": []}
    reply = (
        "if 'id' in request:\n result="
        + repr(payload)
        + " if request['method']=='config/read' else {'userAgent':'codex_cli_rs/1.2.3'}\n print(json.dumps({'id':request['id'],'result':result}),flush=True)"
    )
    client = NativeConfigClient(server_command(tmp_path, reply), tmp_path, timeout=4)
    with client:
        result = client.read()
    requests = [
        json.loads(line)
        for line in (tmp_path / "requests.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [item["method"] for item in requests] == [
        "initialize",
        "initialized",
        "config/read",
    ]
    assert requests[-1]["params"] == {"cwd": str(tmp_path), "includeLayers": True}
    assert result.payload == payload
    assert result.native_version == "1.2.3"
    assert client._process.poll() is not None


@pytest.mark.parametrize(
    "reply,expected",
    [
        ("time.sleep(5)", "observation timeout"),
        (
            "print(json.dumps({'id':request.get('id'),'error':{'code':-1,'message':'"
            + SECRET
            + "'}}),flush=True)",
            "request was rejected",
        ),
        (
            "print(json.dumps({'id':44,'method':'approval','params':{'secret':'"
            + SECRET
            + "'}}),flush=True)",
            "interactive native request refused",
        ),
        ("print('x'*2048,flush=True)", "exceeded bounds or was malformed"),
    ],
)
def test_native_failures_do_not_replay_or_disclose_stderr(
    tmp_path: Path, reply: str, expected: str
) -> None:
    client = NativeConfigClient(
        server_command(tmp_path, reply), tmp_path, timeout=0.5, max_message_bytes=1024
    )
    with pytest.raises(NativeConfigError, match=expected) as error:
        with client:
            client.read()
    assert SECRET not in str(error.value)
    assert client._process.poll() is not None
    requests = (tmp_path / "requests.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(requests) == 1


def test_routes_mode_uses_native_capture_without_transport_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts.ai.codex import native_mcp_config

    class Stub:
        def __init__(self, command: list[str], workspace: Path) -> None:
            assert command == ["installed-codex", "app-server", "--stdio"]
            assert workspace == tmp_path

        def __enter__(self) -> Stub:
            return self

        def read(self) -> ConfigCapture:
            return capture(tmp_path)

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr(native_mcp_config, "NativeConfigClient", Stub)
    monkeypatch.setattr(
        doctor, "profile_plan", lambda *args: {"selected": ["github", "memory"]}
    )
    monkeypatch.setattr(
        doctor,
        "_probe",
        lambda *args: pytest.fail("routes mode must not probe/start MCP"),
    )
    assert (
        doctor.run_routes(
            tmp_path,
            "stable",
            codex_executable=Path("installed-codex"),
            output_json=True,
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["missing"] == ["memory"]
    assert report["readiness_level"] == "configuration"
    assert SECRET not in json.dumps(report)


def test_registered_positional_profile_changes_selection_identity(
    tmp_path: Path,
) -> None:
    value = capture(tmp_path)
    entry = value.payload["config"]["mcp_servers"]["github"]
    entry["args"] = ["-I", "/approved/deja-owner.py", "client", "bioetl-main"]
    before = snapshot(value)["routes"]["github"]
    entry["args"][-1] = "bioetl-other"
    after = snapshot(value)["routes"]["github"]
    assert before["selection"]["chain"]["profile"]["adapter_profile"] == "bioetl-main"
    assert before["selection_fingerprint"] != after["selection_fingerprint"]


def test_unknown_adapter_client_argument_stays_opaque() -> None:
    projected, complete = transport_projection(
        {
            "command": "python",
            "args": [
                "/unreviewed/other-owner.py",
                "client",
                SECRET,
            ],
        }
    )
    assert SECRET not in json.dumps(projected)
    assert "adapter_profile_reference" not in projected
    assert complete is False
