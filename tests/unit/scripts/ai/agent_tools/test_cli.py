"""Contract tests for the optional agent-tool subprocess boundary."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts.ai.agent_tools import __main__ as cli

pytestmark = pytest.mark.unit


@pytest.fixture
def repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide the minimum safe input/output tree and stable source identity."""
    (tmp_path / "reports/ai/agent-tools/inputs").mkdir(parents=True)
    (tmp_path / "tests/fixtures/agent-tools").mkdir(parents=True)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(
        cli,
        "_source_context",
        lambda *_args, **kwargs: {
            "repository": {"repo_id": "bioetl"},
            "source": {
                "head_sha": "fixture-sha",
                "policy_hash": "fixture-policy",
                "scope": kwargs.get("scope"),
            },
        },
    )
    return tmp_path


def _available(spec: cli.ToolSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "distribution": spec.distribution,
        "expected_version": spec.expected_version,
        "installed_version": spec.expected_version,
        "executable": f"/fixture/bin/{spec.executable}",
        "state": "AVAILABLE",
        "exit_code": cli.EXIT_OK,
    }


def _vendor_runner(payload: dict[str, Any], returncode: int = 0):
    def run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        option = "--out" if "--out" in command else "--json"
        output = Path(command[command.index(option) + 1])
        output.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(command, returncode, "vendor stdout", "")

    return run


def test_doctor_is_non_blocking_when_packages_are_absent(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli.importlib.metadata,
        "version",
        lambda _: (_ for _ in ()).throw(cli.importlib.metadata.PackageNotFoundError),
    )
    monkeypatch.setattr(cli, "_executable_path", lambda _: None)

    assert cli.main(["doctor"]) == cli.EXIT_UNAVAILABLE
    payload = json.loads(capsys.readouterr().out)
    assert {tool["state"] for tool in payload["tools"]} == {"UNAVAILABLE"}
    assert payload["policy"]["lifecycle_authority"] is False


def test_doctor_rejects_an_unpinned_installed_version(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli.importlib.metadata, "version", lambda _: "99.0")
    monkeypatch.setattr(cli, "_executable_path", lambda _: Path("/fixture/tool"))

    assert cli.main(["doctor", "--tool", "agentdebugx"]) == cli.EXIT_INCOMPATIBLE
    payload = json.loads(capsys.readouterr().out)
    assert payload["tools"][0]["state"] == "INCOMPATIBLE"


def test_debug_uses_deterministic_subprocess_and_redacts_output(
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    trajectory = repo_root / "tests/fixtures/agent-tools/trajectory.json"
    trajectory.write_text("{}", encoding="utf-8")
    captured: dict[str, Any] = {}

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["env"] = kwargs["env"]
        output = Path(command[command.index("--out") + 1])
        output.write_text(
            json.dumps({"root_cause": "token=vendor-secret"}), encoding="utf-8"
        )
        return subprocess.CompletedProcess(
            command, 0, "Authorization: Bearer vendor-secret", ""
        )

    monkeypatch.setattr(cli, "_tool_status", _available)
    monkeypatch.setattr(cli.subprocess, "run", run)
    monkeypatch.setenv("GITHUB_TOKEN", "must-not-pass")

    assert (
        cli.main(
            [
                "debug",
                "--task-id",
                "fixture-debug",
                "--trajectory",
                str(trajectory),
            ]
        )
        == cli.EXIT_OK
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["verdict"] == "WARN"
    assert summary["advisory"] is True
    assert summary["lifecycle_authority"] is False
    assert summary["optional_evaluator_evidence"] == {
        "schema_version": 1,
        "evidence_kind": "review",
        "producer": "optional_agentdebugx",
        "vendor_verdict": "WARN",
        "receipt_eligible": False,
        "lifecycle_authority": False,
        "source_binding": summary["source"],
    }
    assert "--mode" in captured["command"]
    assert (
        captured["command"][captured["command"].index("--mode") + 1] == "deterministic"
    )
    assert "GITHUB_TOKEN" not in captured["env"]
    assert captured["env"]["LITELLM_LOCAL_MODEL_COST_MAP"] == "true"
    output_dir = repo_root / "reports/ai/agent-tools/agentdebugx/fixture-debug"
    assert "vendor-secret" not in (output_dir / "stdout.txt").read_text(
        encoding="utf-8"
    )
    if sys.platform != "win32":
        assert stat.S_IMODE((output_dir / "summary.json").stat().st_mode) == 0o600


@pytest.mark.parametrize(
    ("certification", "expected"),
    [
        ("GOLD", "PASS"),
        ("SILVER", "WARN"),
        ("NOT_READY", "FAIL"),
        ("", "UNAVAILABLE"),
    ],
)
def test_proofagent_verdict_mapping_is_stable(
    certification: str, expected: str
) -> None:
    assert cli._proof_verdict({"certification": certification}) == expected


def test_evaluate_forces_generic_offline_no_upload_mode(
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    events = repo_root / "reports/ai/agent-tools/inputs/events.jsonl"
    events.write_text('{"tool":"read","target":"README.md"}\n', encoding="utf-8")
    captured: dict[str, list[str]] = {}

    def run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        output = Path(command[command.index("--json") + 1])
        output.write_text(json.dumps({"certification": "GOLD"}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(cli, "_tool_status", _available)
    monkeypatch.setattr(cli.subprocess, "run", run)

    assert (
        cli.main(
            [
                "evaluate",
                "--task-id",
                "fixture-proof",
                "--events",
                str(events),
            ]
        )
        == cli.EXIT_OK
    )
    summary = json.loads(capsys.readouterr().out)
    command = captured["command"]
    assert summary["verdict"] == "PASS"
    assert command[command.index("--tool") + 1] == "generic"
    assert command[command.index("--assess") + 1] == "never"
    assert "--no-upload" in command
    assert "--deny" in command


def test_from_git_requires_explicit_scope(repo_root: Path) -> None:
    assert (
        cli.main(["evaluate", "--task-id", "fixture-proof", "--from-git"])
        == cli.EXIT_USAGE
    )


@pytest.mark.parametrize(
    "value",
    ["../outside.json", ".env", "/tmp/outside.json"],
)
def test_input_allowlist_rejects_unsafe_paths(repo_root: Path, value: str) -> None:
    assert (
        cli.main(
            [
                "debug",
                "--task-id",
                "fixture-debug",
                "--trajectory",
                value,
            ]
        )
        == cli.EXIT_USAGE
    )


def test_task_id_traversal_is_rejected(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trajectory = repo_root / "tests/fixtures/agent-tools/trajectory.json"
    trajectory.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli, "_tool_status", _available)

    assert (
        cli.main(
            [
                "debug",
                "--task-id",
                "../escape",
                "--trajectory",
                str(trajectory),
            ]
        )
        == cli.EXIT_USAGE
    )


def test_timeout_has_stable_exit_code(
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    trajectory = repo_root / "tests/fixtures/agent-tools/trajectory.json"
    trajectory.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli, "_tool_status", _available)

    def timeout(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, 1, output="", stderr="timed out")

    monkeypatch.setattr(cli.subprocess, "run", timeout)
    exit_code = cli.main(
        [
            "debug",
            "--task-id",
            "fixture-timeout",
            "--trajectory",
            str(trajectory),
            "--timeout",
            "1",
        ]
    )
    assert exit_code == cli.EXIT_TIMEOUT
    assert json.loads(capsys.readouterr().out)["status"] == "TIMEOUT"


@pytest.mark.parametrize(
    ("returncode", "write_json", "expected"),
    [(9, True, cli.EXIT_VENDOR_FAILURE), (0, False, cli.EXIT_MALFORMED)],
)
def test_vendor_failure_and_malformed_output_are_distinct(
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    write_json: bool,
    expected: int,
) -> None:
    trajectory = repo_root / "tests/fixtures/agent-tools/trajectory.json"
    trajectory.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli, "_tool_status", _available)

    def run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        if write_json:
            output = Path(command[command.index("--out") + 1])
            output.write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(command, returncode, "", "vendor error")

    monkeypatch.setattr(cli.subprocess, "run", run)
    assert (
        cli.main(
            [
                "debug",
                "--task-id",
                f"fixture-failure-{returncode}",
                "--trajectory",
                str(trajectory),
            ]
        )
        == expected
    )


def test_adapter_does_not_import_vendor_packages() -> None:
    source = Path(cli.__file__).read_text(encoding="utf-8")
    assert "import agentdebug" not in source
    assert "import proofagent_harness" not in source


def test_source_identity_is_explicitly_advisory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path
    monkeypatch.setattr(cli, "ROOT", repo_root)
    policy = {
        "claims": {"ready_to_merge": {"required_evidence": []}},
        "evidence_kinds": {},
    }
    monkeypatch.setattr(cli, "load_policy", lambda _: policy)
    responses = {
        ("rev-parse", "HEAD"): "head-sha",
        ("rev-parse", "HEAD^{tree}"): "tree-sha",
        ("branch", "--show-current"): "main",
    }

    def run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        git_args = tuple(command[command.index(str(repo_root)) + 1 :])
        return subprocess.CompletedProcess(command, 0, responses[git_args], "")

    monkeypatch.setattr(cli.subprocess, "run", run)
    context = cli._source_context()
    assert context["source"]["binding_mode"] == "bounded-advisory-v1"
    assert context["source"]["head_sha"] == "head-sha"
    assert context["source"]["changed_path_inventory"] == "not-collected"
    assert context["source"]["untracked_inventory"] == "not-collected"
    assert context["source"]["tracked_worktree_state"] == "not-collected"
    assert context["source"]["dirty"] is None


def test_platform_entrypoint_names_are_explicit() -> None:
    assert cli.TOOLS["agentdebugx"].executable == "agentdebug"
    assert cli.TOOLS["proofagent"].executable == "proof"
    assert f"{cli.TOOLS['agentdebugx'].executable}.exe" == "agentdebug.exe"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="symlink_to POSIX targets raises WinError 1314 without privilege",
)
def test_executable_lookup_keeps_virtualenv_launcher_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = tmp_path / "venv/bin"
    bin_dir.mkdir(parents=True)
    python = bin_dir / "python"
    executable = bin_dir / "agentdebug"
    python.symlink_to("/usr/bin/python3")
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(cli.sys, "executable", str(python))

    assert cli._executable_path(cli.TOOLS["agentdebugx"]) == executable.resolve()
