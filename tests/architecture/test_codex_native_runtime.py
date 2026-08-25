# pyright: reportUnknownMemberType=false
"""Static CI contract for repository-native Codex discovery and MCP profiles."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
CODEX_SCRIPTS = ROOT / "scripts/ai/codex"
sys.path.insert(0, str(CODEX_SCRIPTS))

import importlib
from tests.architecture.quality_artifacts import (
    load_quality_json,
    quality_artifact_path,
)

doctor = importlib.import_module("doctor")
mcp_profile_contract = importlib.import_module("mcp_profile_contract")
native_runtime_contract = importlib.import_module("native_runtime_contract")


def test_project_config_is_minimal_portable_toml() -> None:
    path = ROOT / ".codex/config.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    assert data == {"agents": {"max_threads": 3}}
    text = path.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in text
    assert "token" not in text.lower()
    assert not any(Path(value).is_absolute() for value in text.split())


def test_project_config_negative_fixture_reports_nonportable_key(
    tmp_path: Path,
) -> None:
    config = tmp_path / ".codex/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[agents]\nmax_threads = 3\napi_key = "bad"\n',
        encoding="utf-8",
    )

    findings = native_runtime_contract.validate_project_config(tmp_path)

    assert any(finding.code == "config.portability" for finding in findings)


def test_project_config_keeps_benchmarked_concurrency_alias(tmp_path: Path) -> None:
    config = tmp_path / ".codex/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[agents]\nmax_concurrent_threads_per_session = 3\n",
        encoding="utf-8",
    )

    findings = native_runtime_contract.validate_project_config(tmp_path)
    messages = [
        finding.message for finding in findings if finding.code == "config.agents"
    ]

    assert messages == [
        "agents.max_threads must equal 3",
        "use agents.max_threads = 3 for the tracked portable baseline; "
        "Codex documents it as the legacy alias for "
        "agents.max_concurrent_threads_per_session",
    ]
    assert all("reject" not in message.lower() for message in messages)


def test_native_agent_inventory_and_fields_are_valid() -> None:
    assert not native_runtime_contract.validate_agents(ROOT)
    toml_names = {path.stem for path in (ROOT / ".codex/agents").glob("py-*.toml")}
    markdown_names = {path.stem for path in (ROOT / ".codex/agents").glob("py-*.md")}
    assert toml_names == markdown_names == set(native_runtime_contract.AGENT_NAMES)


def test_bootstrap_context_budget_and_semantics_are_guarded() -> None:
    stats = native_runtime_contract.bootstrap_corpus_stats(ROOT)

    assert native_runtime_contract.BOOTSTRAP_BASELINE_BYTES == 465_721
    assert native_runtime_contract.BOOTSTRAP_BASELINE_LINES == 8_324
    assert stats["bytes"] <= native_runtime_contract.BOOTSTRAP_MAX_BYTES
    assert 1 - stats["bytes"] / native_runtime_contract.BOOTSTRAP_BASELINE_BYTES >= 0.30
    assert stats["lines"] < native_runtime_contract.BOOTSTRAP_BASELINE_LINES
    assert not native_runtime_contract.validate_runtime_context(ROOT)


def test_runtime_semantic_guard_detects_stale_terms(tmp_path: Path) -> None:
    path = tmp_path / ".codex/agents/ORCHESTRATION.md"
    path.parent.mkdir(parents=True)
    path.write_text("model: sonnet\nuse WebSearch\n", encoding="utf-8")

    findings = native_runtime_contract.validate_runtime_context(tmp_path)

    assert any(
        finding.code == "context.stale" and finding.path.endswith("ORCHESTRATION.md")
        for finding in findings
    )


def test_debug_role_is_strictly_read_only_diagnosis() -> None:
    descriptor = tomllib.loads(
        (ROOT / ".codex/agents/py-debug-bot.toml").read_text(encoding="utf-8")
    )
    profile = (ROOT / ".codex/agents/py-debug-bot.md").read_text(encoding="utf-8")

    assert descriptor["sandbox_mode"] == "read-only"
    assert "remain read-only" in descriptor["developer_instructions"].lower()
    assert "Sandbox: read-only" in profile
    assert "does not modify" in " ".join(profile.split())


def test_native_agent_negative_fixture_identifies_missing_descriptor(
    tmp_path: Path,
) -> None:
    agent_dir = tmp_path / ".codex/agents"
    shutil.copytree(ROOT / ".codex/agents", agent_dir)
    (agent_dir / "py-test-bot.toml").unlink()

    findings = native_runtime_contract.validate_agents(tmp_path)

    assert any(
        finding.code == "agent.missing" and "py-test-bot" in finding.message
        for finding in findings
    )


def test_canonical_skills_are_the_only_project_discovery_surface() -> None:
    assert not native_runtime_contract.validate_canonical_skills(ROOT)
    canonical = native_runtime_contract.canonical_skills(ROOT)
    assert len(canonical) == 14
    assert "agent-debugging" in canonical


def test_skill_negative_fixture_identifies_invalid_canonical_metadata(
    tmp_path: Path,
) -> None:
    shutil.copytree(ROOT / ".codex/skills", tmp_path / ".codex/skills")
    changed = tmp_path / ".codex/skills/py-test-bot/SKILL.md"
    changed.write_text(
        changed.read_text(encoding="utf-8").replace(
            'name: "py-test-bot"', 'name: "wrong"'
        ),
        encoding="utf-8",
    )

    findings = native_runtime_contract.validate_canonical_skills(tmp_path)

    assert any(
        finding.code == "skill.canonical" and "py-test-bot" in finding.message
        for finding in findings
    )


def test_static_doctor_runs_with_fresh_home_without_writes(tmp_path: Path) -> None:
    fresh_home = tmp_path / "fresh-home"
    env = os.environ.copy()
    env["HOME"] = str(fresh_home)
    result = subprocess.run(
        [
            sys.executable,
            str(CODEX_SCRIPTS / "doctor.py"),
            "static",
            "--no-write",
            "--repo-root",
            str(ROOT),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert "[OK]" in result.stdout
    assert not fresh_home.exists()


def test_mcp_profile_matrix_required_and_optional_sets() -> None:
    assert not mcp_profile_contract.validate_profile_matrix(ROOT)
    shared = mcp_profile_contract.profile_plan("shared", ROOT)
    stable = mcp_profile_contract.profile_plan("stable", ROOT)
    core = mcp_profile_contract.profile_plan("core", ROOT)
    graph = mcp_profile_contract.profile_plan("graph", ROOT)

    assert {"mermaid", "neo4j-cypher", "neo4j-memory"} <= set(shared["optional"])
    assert "deepwiki" not in set(stable["selected"])
    assert "deepwiki" in set(shared["optional"])
    assert "ref" in set(stable["selected"])
    assert "mermaid" in set(core["required"])
    assert {"neo4j-cypher", "neo4j-memory"} <= set(graph["required"])


def test_mcp_doctor_warns_for_shared_optional_failure_and_fails_required(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    down = {"mermaid", "neo4j-cypher", "neo4j-memory"}

    def fake_probe(
        name: str, entry: dict[str, object], timeout: float
    ) -> dict[str, object]:
        del entry, timeout
        ready = name not in down
        return {
            "server": name,
            "url": f"mock://{name}",
            "port_open": ready,
            "ping_ok": ready,
            "ready": ready,
            "detail": "mock ready" if ready else "mock unavailable",
            "elapsed_ms": 1,
        }

    monkeypatch.setattr(doctor, "_probe", fake_probe)
    shared_status = doctor.run_mcp(
        ROOT,
        "shared",
        timeout=0.1,
        overall_timeout=2.0,
        output_json=False,
    )
    shared_output = capsys.readouterr().out
    core_status = doctor.run_mcp(
        ROOT,
        "core",
        timeout=0.1,
        overall_timeout=2.0,
        output_json=False,
    )
    core_output = capsys.readouterr().out
    graph_status = doctor.run_mcp(
        ROOT,
        "graph",
        timeout=0.1,
        overall_timeout=2.0,
        output_json=False,
    )
    graph_output = capsys.readouterr().out

    assert shared_status == 0
    assert "[WARN] mermaid optional" in shared_output
    assert core_status == 1
    assert "[FAIL] mermaid required" in core_output
    assert graph_status == 1
    assert "[FAIL] neo4j-cypher required" in graph_output
    assert (
        "[HINT] For daily readiness, select the stable/shared profile" in graph_output
    )


def test_mcp_report_path_is_explicit_and_governed(tmp_path: Path) -> None:
    quality_report = Path("reports/quality/codex-mcp-health.json")

    assert (
        doctor._governed_report_path(tmp_path, quality_report)
        == (tmp_path / quality_report).resolve()
    )
    with pytest.raises(ValueError, match="under reports/quality"):
        doctor._governed_report_path(tmp_path, Path("logs/mcp-health.json"))
    with pytest.raises(ValueError, match=r"\.json suffix"):
        doctor._governed_report_path(tmp_path, Path("reports/quality/mcp.txt"))
    with pytest.raises(ValueError, match="repository-relative"):
        doctor._governed_report_path(
            tmp_path,
            tmp_path / "reports/quality/mcp.json",
        )
    with pytest.raises(ValueError, match="parent traversal"):
        doctor._governed_report_path(
            tmp_path,
            Path("reports/quality/../quality/mcp.json"),
        )


def test_mcp_report_path_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    quality_root = tmp_path / "reports/quality"
    quality_root.mkdir(parents=True)
    link = quality_root / "external"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ValueError, match="under reports/quality"):
        doctor._governed_report_path(
            tmp_path,
            Path("reports/quality/external/mcp.json"),
        )


def test_mcp_doctor_writes_only_to_explicit_quality_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    catalog = tmp_path / "scripts/ops/runtime/mcp/shared-servers.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text('{"servers": {}}\n', encoding="utf-8")
    monkeypatch.setattr(
        doctor,
        "profile_plan",
        lambda _profile, _repo_root: {
            "required_local": [],
            "optional_local": [],
            "remote_or_external": [],
        },
    )

    assert (
        doctor.run_mcp(
            tmp_path,
            "stable",
            timeout=0.1,
            overall_timeout=0.1,
            output_json=False,
        )
        == 0
    )
    assert not (tmp_path / "logs").exists()
    output = Path("reports/quality/codex-mcp-health.json")
    assert (
        doctor.run_mcp(
            tmp_path,
            "stable",
            timeout=0.1,
            overall_timeout=0.1,
            output_json=False,
            output_path=output,
        )
        == 0
    )
    assert (tmp_path / output).is_file()


def test_native_runtime_workflow_has_complete_path_filters_and_static_job() -> None:
    workflow = (ROOT / ".github/workflows/skills-consistency.yml").read_text(
        encoding="utf-8"
    )
    for owner_path in (
        ".codex/config.toml",
        ".codex/agents/**",
        ".codex/skills/**",
        "scripts/ai/codex/doctor.py",
        "scripts/ai/codex/setup_mcp.py",
    ):
        assert workflow.count(f'"{owner_path}"') == 2
    assert "python3 scripts/ai/codex/doctor.py static --no-write" in workflow


def test_shared_catalog_daily_flag_matches_stable_local_inventory() -> None:
    catalog = json.loads(
        (ROOT / "scripts/ops/runtime/mcp/shared-servers.json").read_text(
            encoding="utf-8"
        )
    )["servers"]
    daily = {name for name, entry in catalog.items() if entry["daily"]}
    stable_local = set(
        mcp_profile_contract.profile_plan("stable", ROOT)["required_local"]
    )
    assert daily == stable_local
