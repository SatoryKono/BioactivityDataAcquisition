"""Source-bound regressions for BIOETL-AGENT-AUDIT-20261106-R1."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[6]
pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def _native_bash() -> str:
    if os.name == "nt":
        from scripts.engineering.qa.run_local_coverage_verify import _windows_bash

        return _windows_bash()
    executable = shutil.which("bash")
    if not executable:
        pytest.skip("Native Bash unavailable")
    return executable


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_metrics_unknown_then_first_and_second_observation(tmp_path: Path) -> None:
    module = load_module(
        "audit_metrics", ROOT / ".devin/scripts/collect_agent_metrics.py"
    )
    collector = module.AgentMetricsCollector(tmp_path / "metrics.json")
    collector.metrics["agents"]["fixture"] = {
        "call_count": 0,
        "average_duration_ms": None,
        "success_rate": None,
        "last_used": None,
        "common_modes": [],
        "typical_scope": [],
    }
    collector.record_agent_call("fixture", 0, False)
    collector.record_agent_call("fixture", 100, True)
    assert collector.metrics["agents"]["fixture"]["average_duration_ms"] == 50
    assert collector.metrics["agents"]["fixture"]["success_rate"] == 0.5
    collector.record_skill_call("fixture", 20)
    collector.record_workflow_call("fixture", 20, False)
    collector.record_mcp_call("fixture", 20)
    collector.save_metrics()
    assert (
        module.AgentMetricsCollector(collector.metrics_path).metrics
        == collector.metrics
    )


def test_metrics_legacy_naive_timestamp_still_reports_unused_server(
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime

    module = load_module(
        "legacy_metrics", ROOT / ".devin/scripts/collect_agent_metrics.py"
    )

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 6, tzinfo=tz or UTC)

    module.datetime = FixedDateTime
    collector = module.AgentMetricsCollector(tmp_path / "metrics.json")
    collector.metrics["mcp_servers"] = {
        "legacy": {"call_count": 5, "last_used": "2026-09-01T12:00:00"},
        "aware": {"call_count": 5, "last_used": "2026-09-01T12:00:00+00:00"},
        "recent": {"call_count": 5, "last_used": "2026-11-01T12:00:00"},
    }
    result = collector.analyze_mcp_usage(30)
    unused = next(
        item["servers"]
        for item in result["recommendations"]
        if item["type"] == "unused_servers"
    )
    assert unused == ["legacy (unused for 30+ days)", "aware (unused for 30+ days)"]


def test_neo4j_diagnostic_accepts_combined_auth_without_backend(tmp_path: Path) -> None:
    bash = _native_bash()
    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name, body in {
        "codex": '#!/bin/sh\ncase "$*" in *list*) echo "neo4j-memory stdio enabled";; *) echo mcp_neo4j_memory_wrapper;; esac\n',
        "nc": "#!/bin/sh\nexit 0\n",
        "docker": "#!/bin/sh\necho bioetl-neo4j\n",
    }.items():
        executable = binaries / name
        executable.write_text(body, encoding="utf-8")
        executable.chmod(0o755)
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("NEO4J_")
    }
    env.update(
        PATH=str(binaries) + os.pathsep + env.get("PATH", ""),
        BIOETL_REPO_ENV_LOADED="1",
        NEO4J_AUTH="fixture-user/fixture-password",
    )
    result = subprocess.run(
        [bash, (ROOT / "scripts/ai/mcp/check_neo4j_memory.sh").as_posix()],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Configured username: fixture-user" in result.stdout
    assert "required; no credential default" not in result.stderr


def test_metrics_load_migrates_zero_samples_without_fabricating_measurements(
    tmp_path: Path,
) -> None:
    module = load_module(
        "audit_metrics_migration", ROOT / ".devin/scripts/collect_agent_metrics.py"
    )
    source = tmp_path / "metrics.json"
    source.write_text(
        json.dumps(
            {
                "agents": {
                    "unused": {
                        "call_count": 0,
                        "average_duration_ms": 0,
                        "success_rate": 0.0,
                    }
                },
                "skills": {},
                "workflows": {},
                "mcp_servers": {},
            }
        ),
        encoding="utf-8",
    )
    collector = module.AgentMetricsCollector(source)
    assert collector.metrics["agents"]["unused"]["average_duration_ms"] is None
    assert collector.metrics["agents"]["unused"]["success_rate"] is None
    assert (
        json.loads(source.read_text(encoding="utf-8"))["agents"]["unused"][
            "success_rate"
        ]
        == 0.0
    )


def test_doctor_deadline_does_not_hold_process_until_worker_finishes() -> None:
    body = "import sys,time;sys.path.insert(0,'scripts/ai/codex');import doctor;doctor._probe=lambda *args:time.sleep(10);r=doctor._run_profile_probes({'fixture':{'port':1}},['fixture'],{'fixture'},timeout=10,overall_timeout=0.05);print(r[0]['ready'])"
    completed = subprocess.run(
        [sys.executable, "-c", body],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "False"


@pytest.mark.parametrize(
    "mode,disabled", [("off", True), ("read-only", True), ("read-write", False)]
)
def test_effective_memory_requirements_follow_task_mode(
    monkeypatch: pytest.MonkeyPatch, mode: str, disabled: bool
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts/ai/codex"))
    import mcp_profile_contract

    monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", mode)
    declared = mcp_profile_contract.profile_plan("stable", ROOT)
    effective = mcp_profile_contract.effective_profile_plan(declared)
    assert "memory" in declared["required_local"]
    assert ("memory" not in effective["required_local"]) == disabled


@pytest.mark.parametrize(
    "explicit", [None, "off", "read-only", "read-write", "", "   ", " read-write "]
)
def test_memory_readiness_uses_repository_mode_without_exporting_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, explicit: str | None
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts/ai/codex"))
    import mcp_profile_contract

    fixture = tmp_path / "repository-config.fixture"
    fixture.write_text(
        '# config\nBIOETL_AI_MEMORY_MODE = "read-write"\nUNRELATED_SECRET=fixture-only\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("BIOETL_ENV_FILE", str(fixture))
    monkeypatch.delenv("BIOETL_REPO_ENV_LOADED", raising=False)
    monkeypatch.delenv("BIOETL_AI_MEMORY_MODE", raising=False)
    monkeypatch.delenv("UNRELATED_SECRET", raising=False)
    if explicit is not None:
        monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", explicit)
    before = dict(os.environ)
    declared = mcp_profile_contract.profile_plan("stable", ROOT)
    effective = mcp_profile_contract.effective_profile_plan(declared)
    assert ("memory" in effective["required_local"]) == (
        explicit in {None, "", "read-write", " read-write "}
    )
    assert dict(os.environ) == before
    assert "fixture-only" not in json.dumps(effective)


@pytest.mark.parametrize(
    "config_value", ["rw # inline comment", '" read-write "', '" rw " # inline comment']
)
def test_memory_readiness_defaults_to_root_env_without_writing_env_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, config_value: str
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts/ai/codex"))
    import mcp_profile_contract

    for key in ("BIOETL_AI_MEMORY_MODE", "BIOETL_ENV_FILE", "BIOETL_REPO_ENV_LOADED"):
        monkeypatch.delenv(key, raising=False)
    source = tmp_path / ".env"
    original_is_file, original_read_text = Path.is_file, Path.read_text
    monkeypatch.setattr(
        Path, "is_file", lambda path: path == source or original_is_file(path)
    )
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, *args, **kwargs: (
            f"BIOETL_AI_MEMORY_MODE={config_value}\n"
            if path == source
            else original_read_text(path, *args, **kwargs)
        ),
    )
    declared = mcp_profile_contract.profile_plan("stable", ROOT)
    effective = mcp_profile_contract.effective_profile_plan(declared, tmp_path)
    assert "memory" in effective["required_local"]
    monkeypatch.setenv("BIOETL_REPO_ENV_LOADED", "1")
    loaded = mcp_profile_contract.effective_profile_plan(declared, tmp_path)
    assert "memory" not in loaded["required_local"]


def test_skills_ci_covers_audited_direct_inputs() -> None:
    config = yaml.safe_load(
        (ROOT / ".github/workflows/skills-consistency.yml").read_text(encoding="utf-8")
    )
    events = config.get("on", config.get(True))
    for event in ("push", "pull_request"):
        for name in (
            ".devin/skills/py-test-bot/SKILL.md",
            "scripts/ai/mcp/wrappers.py",
            "scripts/ai/sync/governance.py",
            "scripts/ops/support/skills/check_skills_mirror.sh",
            "scripts/engineering/common/platform.py",
            "scripts/ops/runtime/mcp/shared-servers.json",
            "docs/00-project/ai/skills/local/py-test-bot/SKILL.md",
        ):
            assert any(
                fnmatchcase(name, pattern) for pattern in events[event]["paths"]
            ), name
        assert not any(
            fnmatchcase("data/unrelated.csv", pattern)
            for pattern in events[event]["paths"]
        )


def test_opencode_last_match_permissions_allow_reads_and_gate_writes() -> None:
    text = (ROOT / ".opencode/agent/review.md").read_text(encoding="utf-8")
    rules = yaml.safe_load(text.split("---", 2)[1])["permission"]["bash"]

    def resolve(command: str) -> str:
        return [
            value for pattern, value in rules.items() if fnmatchcase(command, pattern)
        ][-1]

    for command in (
        "git status --porcelain",
        "git rev-parse HEAD",
    ):
        assert resolve(command) == "allow"
    for command in (
        "git diff --output=review.patch origin/main...HEAD",
        "git show --output=review.patch HEAD",
        "git log --output=review.patch",
        "git push",
        "gh pr merge 1",
        "gh pr review --approve 1",
    ):
        assert resolve(command) == "deny"
    assert resolve("gh pr comment 1") == "ask"
    assert resolve("gh pr view 1") == "ask"
    assert resolve("gh pr diff 1") == "ask"
    assert resolve("gh pr diff 1 > .env") != "allow"


def test_github_powershell_child_env_is_isolated(tmp_path: Path) -> None:
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 is unavailable")
    # Python is a fixture executable; its script is named stdio to accept the
    # launcher's real first argument without starting a server or network call.
    (tmp_path / "stdio").write_text(
        "import os,sys,json;print(json.dumps({'unrelated':'OPENAI_API_KEY' in os.environ,'github':'GITHUB_PERSONAL_ACCESS_TOKEN' in os.environ,'args':sys.argv[1:]}))",
        encoding="utf-8",
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(
            word in key.upper()
            for word in ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "NEO4J")
        )
    }
    env.update(
        BIOETL_REPO_ENV_LOADED="1",
        BIOETL_GITHUB_MCP_SERVER=sys.executable,
        GITHUB_PERSONAL_ACCESS_TOKEN="ghp_synthetic_fixture_only_123456789",
        OPENAI_API_KEY="synthetic-unrelated",
        NEO4J_AUTH="malformed-fixture",
        BIOETL_GITHUB_MCP_ACCESS="read-only",
    )
    # The fixture exercises the native binary boundary, independently of an
    # operator's optional managed-route file. Mock only that host discovery;
    # do not modify production routing or credential policy.
    env.pop("PC_AGENT_GITHUB_PROJECT_ROUTES", None)
    env.pop("BIOETL_GITHUB_MCP_SHA256", None)
    env.pop("BIOETL_MCP_VALIDATE_ONLY", None)
    env["BIOETL_TEST_WRAPPER_PATH"] = str(
        ROOT / "scripts/ai/mcp/github-mcp-wrapper.ps1"
    )
    launch = tmp_path / "launch-fixture.ps1"
    launch.write_text(
        r"""function global:Test-Path {
    [CmdletBinding()]
    param([Parameter(Position=0)][string]$Path, [string]$LiteralPath, [string]$PathType)
    $candidate = if ($PSBoundParameters.ContainsKey('LiteralPath')) { $LiteralPath } else { $Path }
    if ($candidate -match '[/\\]\.config[/\\]pc-agent[/\\]github-project-route\.json$') { return $false }
    Microsoft.PowerShell.Management\Test-Path @PSBoundParameters
}
& $env:BIOETL_TEST_WRAPPER_PATH
exit $LASTEXITCODE
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            pwsh,
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(launch),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["github"] is True and payload["unrelated"] is False
    assert "--read-only" in payload["args"]
    assert "synthetic-unrelated" not in completed.stdout + completed.stderr


def test_doctor_reports_transport_without_claiming_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from contextlib import nullcontext
    from types import SimpleNamespace

    monkeypatch.syspath_prepend(str(ROOT / "scripts/ai/codex"))
    import doctor

    monkeypatch.setattr(
        doctor.socket, "create_connection", lambda *a, **kw: nullcontext()
    )
    monkeypatch.setattr(
        doctor.urllib.request,
        "urlopen",
        lambda *a, **kw: nullcontext(SimpleNamespace(status=200)),
    )
    result = doctor._probe("fixture", {"port": 1}, 0.1)
    assert result["transport_ready"] is True
    assert result["protocol_ready"] is None and result["tool_ready"] is None
    assert result["readiness_level"] == "transport"


@pytest.mark.parametrize("shell", ["powershell", "bash"])
def test_filesystem_validate_only_creates_no_cache(tmp_path: Path, shell: str) -> None:
    env = dict(
        os.environ,
        BIOETL_REPO_ENV_LOADED="1",
        BIOETL_MCP_VALIDATE_ONLY="1",
        NPM_CONFIG_CACHE=str(tmp_path / "never-created"),
    )
    if shell == "powershell":
        executable = shutil.which("pwsh")
        if not executable:
            pytest.skip("PowerShell 7 unavailable")
        command = [
            executable,
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(ROOT / "scripts/ai/mcp/mcp_filesystem_wrapper.ps1"),
        ]
    else:
        executable = (
            str(
                Path(os.environ.get("ProgramFiles", "C:/Program Files"))
                / "Git/bin/bash.exe"
            )
            if os.name == "nt"
            else shutil.which("bash")
        )
        if not executable or not Path(executable).exists():
            pytest.skip("Native Bash unavailable")
        command = [executable, str(ROOT / "scripts/ai/mcp/mcp_filesystem_wrapper.sh")]
    completed = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=15
    )
    assert completed.returncode == 0, completed.stderr
    assert not (tmp_path / "never-created").exists()


@pytest.mark.parametrize(
    "access,digest",
    [("read-only", None), ("read-only", "0" * 64), ("read-write", None)],
)
def test_github_bash_isolates_env_and_checks_identity(
    tmp_path: Path, access: str, digest: str | None
) -> None:
    executable = (
        str(
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "Git/bin/bash.exe"
        )
        if os.name == "nt"
        else shutil.which("bash")
    )
    if not executable or not Path(executable).exists():
        pytest.skip("Native Bash unavailable")
    (tmp_path / "stdio").write_text(
        "import os,sys,json;print(json.dumps({'unrelated':'OPENAI_API_KEY' in os.environ,'github':'GITHUB_PERSONAL_ACCESS_TOKEN' in os.environ,'args':sys.argv[1:]}))",
        encoding="utf-8",
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(
            word in key.upper()
            for word in ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "NEO4J")
        )
    }
    env.update(
        BIOETL_REPO_ENV_LOADED="1",
        BIOETL_GITHUB_MCP_SERVER=sys.executable,
        GITHUB_PERSONAL_ACCESS_TOKEN="ghp_synthetic_fixture_only_123456789",
        OPENAI_API_KEY="synthetic-unrelated",
        NEO4J_AUTH="malformed-fixture",
        BIOETL_GITHUB_MCP_ACCESS=access,
        GITHUB_EXCLUDE_TOOLS="custom_fixture",
    )
    env.pop("BIOETL_GITHUB_MCP_SHA256", None)
    env.pop("BIOETL_MCP_VALIDATE_ONLY", None)
    if digest:
        env["BIOETL_GITHUB_MCP_SHA256"] = digest
    # Exercise native launch with a local fixture, independent of the host's
    # managed GitHub route. Exit 78 is the transport's documented no-route
    # result; the fixture never contacts an owner or a remote service.
    env.pop("PC_AGENT_GITHUB_PROJECT_ROUTES", None)
    fixture_bin = tmp_path / "bin"
    fixture_bin.mkdir()
    node = fixture_bin / "node"
    node.write_text(
        '#!/bin/sh\ncase "${1##*/}" in github_project_transport.mjs) exit 78;; *) exit 99;; esac\n',
        encoding="utf-8",
    )
    node.chmod(0o755)
    env["PATH"] = str(fixture_bin) + os.pathsep + env.get("PATH", "")
    completed = subprocess.run(
        [executable, str(ROOT / "scripts/ai/mcp/github-mcp-wrapper.sh")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if digest or access == "read-write":
        assert completed.returncode != 0
        assert not completed.stdout
    else:
        assert completed.returncode == 0, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["github"] is True and payload["unrelated"] is False
        assert "--read-only" in payload["args"]
        assert (
            "merge_pull_request"
            in payload["args"][payload["args"].index("--exclude-tools") + 1]
        )
