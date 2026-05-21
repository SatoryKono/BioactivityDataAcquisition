from __future__ import annotations

from pathlib import Path
import re
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _git_ls_files(*patterns: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", *patterns],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return [line for line in result.stdout.splitlines() if line]

    # Windows / mixed-checkout git invocations occasionally fail even though the
    # governance invariant is simply "no tracked concepts/ surface remains".
    # Fall back to a filesystem scan so local empty/untracked directories do not
    # trip the test while still surfacing tracked-looking files if they exist.
    concepts_root = ROOT / "concepts"
    if not concepts_root.exists():
        return []

    tracked_like_paths: list[str] = []
    for path in concepts_root.rglob("*"):
        if any(part.startswith(".") for part in path.relative_to(concepts_root).parts):
            continue
        if path.is_file():
            tracked_like_paths.append(path.relative_to(ROOT).as_posix())
    return sorted(tracked_like_paths)


def test_adr_003_status_is_superseded_across_governance_surfaces() -> None:
    adr_text = _read(
        "docs/02-architecture/decisions/ADR-003-in-memory-locking-strategy.md"
    )
    adr_index_text = _read("docs/02-architecture/decisions/README.md")
    rules_text = _read("docs/00-project/RULES.md")

    assert "ADR-003" in adr_text
    assert "ADR-010" in adr_text
    assert re.search(r"status\s*:\s*superseded", adr_text, re.IGNORECASE)
    assert re.search(r"ADR-003.*\bSuperseded\b", adr_index_text, re.IGNORECASE)
    assert re.search(r"ADR-003.*\bSuperseded\b", rules_text, re.IGNORECASE)


def test_technical_debt_summary_tracks_live_exemption_baseline() -> None:
    summary_text = _read("docs/reports/evidence/technical-debt/SUMMARY.md")
    scorecard = yaml.safe_load(_read("configs/quality/debt_scorecard.yaml"))
    baseline = scorecard["baseline"]
    file_size_limits = baseline["by_registry"]["file_size_limits"]

    assert f"`{file_size_limits}` active file-size-limit exemptions" in summary_text
    assert "не содержит active class/god-object" in summary_text


def test_root_governance_ratifies_reviewed_docker_helpers() -> None:
    allowlist_text = _read(".github/root-allowlist.txt")
    file_policy_text = _read("docs/00-project/governance/03-file-policy.md")
    docker_quickstart_text = _read("docs/DOCKER_QUICKSTART.md")
    docker_setup_text = _read("docs/DOCKER_SETUP.md")

    for filename in (
        "docker-compose.alertmanager.yml",
        "docker-compose.minio.yml",
        "docker-compose.redis.yml",
        "docker-compose.sonarqube.yml",
    ):
        assert filename in allowlist_text
        assert filename in docker_quickstart_text
        assert filename in docker_setup_text

    assert "helper stacks" in file_policy_text
    assert "local-only" in file_policy_text
    assert "canonical" in docker_quickstart_text
    assert "helper flow" in docker_quickstart_text
    assert "ADR-010" in docker_setup_text
    assert "canonical orchestration path" in docker_setup_text
    assert "docker network create bioetl-monitoring" in docker_quickstart_text
    assert "docker network create bioetl-monitoring" in docker_setup_text


def test_canonical_docker_helpers_bootstrap_shared_external_networks() -> None:
    bash_helper = _read("scripts/ops/docker-setup.sh")
    powershell_helper = _read("scripts/ops/docker-setup.ps1")

    for helper_text in (bash_helper, powershell_helper):
        assert "bioetl-monitoring" in helper_text
        assert "warp-network" in helper_text
        assert "docker network inspect" in helper_text
        assert "docker network create" in helper_text


def test_concepts_root_surface_is_retired_from_repo_root() -> None:
    assert _git_ls_files("concepts", "concepts/**") == [], (
        "Root-level concepts/ surface must remain retired from the repository root"
    )
