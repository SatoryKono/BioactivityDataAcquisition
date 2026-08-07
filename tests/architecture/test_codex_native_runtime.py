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


def test_native_agent_inventory_and_fields_are_valid() -> None:
    assert not native_runtime_contract.validate_agents(ROOT)
    toml_names = {path.stem for path in (ROOT / ".codex/agents").glob("py-*.toml")}
    markdown_names = {path.stem for path in (ROOT / ".codex/agents").glob("py-*.md")}
    assert toml_names == markdown_names == set(native_runtime_contract.AGENT_NAMES)


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
    assert not native_runtime_contract.validate_skill_adapters(ROOT)
    canonical = native_runtime_contract.canonical_skills(ROOT)
    assert len(canonical) == 13
    assert not any((ROOT / ".agents/skills").glob("*/SKILL.md"))


def test_native_skill_projection_root_is_tracked_tooling() -> None:
    catalog = yaml.safe_load(
        (ROOT / "configs/quality/repo_structure_catalog.yaml").read_text(
            encoding="utf-8"
        )
    )
    tracked = {
        entry["path"] for entry in catalog["root_tooling_roots"]["approved_roots"]
    }
    local_only = {
        entry["path"]
        for entry in catalog["local_tolerated_root_dirs"]["approved_roots"]
    }

    assert ".agents" in tracked
    assert ".agents" not in local_only


def test_skill_negative_fixture_identifies_invalid_canonical_metadata(tmp_path: Path) -> None:
    shutil.copytree(ROOT / ".codex/skills", tmp_path / ".codex/skills")
    changed = tmp_path / ".codex/skills/py-test-bot/SKILL.md"
    changed.write_text(
        changed.read_text(encoding="utf-8").replace('name: "py-test-bot"', 'name: "wrong"'),
        encoding="utf-8",
    )

    findings = native_runtime_contract.validate_skill_adapters(tmp_path)

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
    core = mcp_profile_contract.profile_plan("core", ROOT)
    graph = mcp_profile_contract.profile_plan("graph", ROOT)

    assert {"mermaid", "neo4j-cypher", "neo4j-memory"} <= set(shared["optional"])
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
        no_write=True,
        output_json=False,
    )
    shared_output = capsys.readouterr().out
    core_status = doctor.run_mcp(
        ROOT,
        "core",
        timeout=0.1,
        overall_timeout=2.0,
        no_write=True,
        output_json=False,
    )
    core_output = capsys.readouterr().out
    graph_status = doctor.run_mcp(
        ROOT,
        "graph",
        timeout=0.1,
        overall_timeout=2.0,
        no_write=True,
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


def test_native_runtime_workflow_has_complete_path_filters_and_static_job() -> None:
    workflow = (ROOT / ".github/workflows/skills-consistency.yml").read_text(
        encoding="utf-8"
    )
    for owner_path in (
        ".codex/config.toml",
        ".codex/agents/**",
        ".codex/skills/**",
        ".agents/skills/**",
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
