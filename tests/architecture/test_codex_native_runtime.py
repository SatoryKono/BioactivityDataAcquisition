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
import yaml

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
CODEX_SCRIPTS = ROOT / "scripts/ai/codex"
sys.path.insert(0, str(CODEX_SCRIPTS))

import importlib

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
    shared_status = doctor.run_transport(
        ROOT,
        "shared",
        timeout=0.1,
        overall_timeout=2.0,
        output_json=False,
    )
    shared_output = capsys.readouterr().out
    core_status = doctor.run_transport(
        ROOT,
        "core",
        timeout=0.1,
        overall_timeout=2.0,
        output_json=False,
    )
    core_output = capsys.readouterr().out
    graph_status = doctor.run_transport(
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
        doctor.run_transport(
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
        doctor.run_transport(
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
    """Codex runtime checks stay gated via the CircleCI lane.

    After the coordinator cutover, automatic coverage moved from leaf
    workflow path filters to the unconditional ``skills-consistency`` job in
    ``pr-gate``; the Actions workflow keeps the manual dispatch path.
    """
    config = yaml.safe_load(
        (ROOT / ".circleci" / "config.yml").read_text(encoding="utf-8")
    )
    job = config["jobs"]["skills-consistency"]
    commands = " ".join(
        step["run"]["command"]
        for step in job["steps"]
        if isinstance(step, dict) and isinstance(step.get("run"), dict)
    )
    assert "python scripts/ai/codex/doctor.py static --no-write" in commands
    assert "python -m scripts.ai.mcp wrappers check" in commands
    workflow = (ROOT / ".github/workflows/skills-consistency.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in workflow
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


@pytest.mark.parametrize("runtime", [".codex", ".junie", ".devin"])
@pytest.mark.parametrize("suffix", [".md", ".toml"])
def test_skill_allowlists_reject_unresolved_routes(
    tmp_path: Path, runtime: str, suffix: str
) -> None:
    agent = tmp_path / runtime / "agents" / ("py-test-bot" + suffix)
    agent.parent.mkdir(parents=True)
    skill = tmp_path / runtime / "skills/valid/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("valid entrypoint", encoding="utf-8")
    agent.write_text(
        "Allowed skills: `valid`,\n`missing-skill` opt-in.\nAllowed MCP: ast-grep.",
        encoding="utf-8",
    )
    findings = native_runtime_contract.validate_skill_routes(tmp_path)
    assert len(findings) == 1
    assert findings[0].code == "skill.route"
    assert "missing-skill" in findings[0].message
    agent.write_text("Allowed skills: valid. Allowed MCP: ast-grep.", encoding="utf-8")
    assert native_runtime_contract.validate_skill_routes(tmp_path) == []
    agent.write_text(
        "Allowed skills: valid/valid. Allowed MCP: ast-grep.", encoding="utf-8"
    )
    assert (
        native_runtime_contract.validate_skill_routes(tmp_path)[0].code == "skill.route"
    )


def test_project_agent_skill_allowlists_resolve() -> None:
    assert native_runtime_contract.validate_skill_routes(ROOT) == []


@pytest.mark.parametrize("runtime", [".codex", ".junie", ".devin"])
def test_research_skill_uses_portable_current_agent_workflow(runtime: str) -> None:
    text = (ROOT / runtime / "skills/research-workflow/SKILL.md").read_text(
        encoding="utf-8"
    )
    metadata = yaml.safe_load(text.split("---", 2)[1])
    assert "context" not in metadata
    assert "agent" not in metadata
    assert "AskUserQuestion" not in text
    assert "plain-text question" in text
    assert "never expands permissions" in text


def test_rule_inventory_never_promotes_present_sources_to_loaded(
    tmp_path: Path,
) -> None:
    (tmp_path / "AGENTS.md").write_text("Project rules", encoding="utf-8")
    (tmp_path / "AGENTS.override.md").write_text("Override", encoding="utf-8")
    config = tmp_path / ".devin/config.json"
    config.parent.mkdir()
    config.write_text('{"read_config_from":{"agents_standard":true}}', encoding="utf-8")

    report = native_runtime_contract.rule_loading_inventory(tmp_path)

    assert report["status"] == "NOT_PROVEN"
    assert report["runtime_process_started"] is False
    assert {item["runtime"] for item in report["runtimes"]} == {
        "codex",
        "junie",
        "devin",
        "opencode",
    }
    for runtime in report["runtimes"]:
        assert runtime["version"] is None
        assert runtime["model_execution"] == "NOT_PROVEN"
        for source in runtime["sources"]:
            assert source["loading"] == "NOT_PROVEN"
            assert source["execution"] == "NOT_PROVEN"
    devin = next(item for item in report["runtimes"] if item["runtime"] == "devin")
    config_source = next(
        item for item in devin["sources"] if item["connection"] == "configuration"
    )
    assert config_source["declared_agents_standard"] is True
    assert config_source["presence"] == "PRESENT"
    assert len(config_source["sha256"]) == 64


@pytest.mark.parametrize("raw", ['{"read_config_from":[]}', "DO_NOT_LEAK_SENTINEL"])
def test_rule_inventory_sanitizes_invalid_configuration(
    tmp_path: Path, raw: str
) -> None:
    config = tmp_path / ".devin/config.json"
    config.parent.mkdir()
    config.write_text(raw, encoding="utf-8")
    report = native_runtime_contract.rule_loading_inventory(tmp_path)
    devin = next(item for item in report["runtimes"] if item["runtime"] == "devin")
    source = next(
        item for item in devin["sources"] if item["connection"] == "configuration"
    )
    assert source["presence"] == "ERROR"
    assert "DO_NOT_LEAK_SENTINEL" not in json.dumps(report)


def test_rule_inventory_bounds_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(native_runtime_contract, "RULE_SOURCE_MAX_BYTES", 10)
    (tmp_path / "AGENTS.md").write_text("x" * 11, encoding="utf-8")
    source = native_runtime_contract.rule_loading_inventory(tmp_path)["runtimes"][0][
        "sources"
    ][1]
    assert source["presence"] == "ERROR"
    assert "sha256" not in source


def test_rules_mode_does_not_execute_tools_or_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "AGENTS.md").write_text("Project rules", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["doctor.py", "rules", "--no-write", "--json", "--repo-root", str(tmp_path)],
    )
    monkeypatch.setattr(
        doctor, "run_static", lambda *a, **k: pytest.fail("static gate called")
    )
    monkeypatch.setattr(doctor, "run_mcp", lambda *a, **k: pytest.fail("MCP called"))
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: pytest.fail("process started")
    )
    monkeypatch.setattr(Path, "write_text", lambda *a, **k: pytest.fail("file write"))
    assert doctor.main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "NOT_PROVEN"


@pytest.mark.parametrize("target", ["external", "protected"])
def test_rule_inventory_rejects_resolved_source_before_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    source = tmp_path / "AGENTS.md"
    source.write_text("candidate", encoding="utf-8")
    destination = (
        tmp_path.parent / "outside-rules.md"
        if target == "external"
        else tmp_path / ".env.protected"
    )
    original_resolve = Path.resolve
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda path, *a, **k: (
            destination if path == source else original_resolve(path, *a, **k)
        ),
    )
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("protected read"))
    result = native_runtime_contract._rule_source(tmp_path, source, "native_candidate")
    assert result["presence"] == "ERROR"
    assert "sha256" not in result
