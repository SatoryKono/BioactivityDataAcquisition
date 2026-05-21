from __future__ import annotations

from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_adr_003_status_is_superseded_across_governance_surfaces() -> None:
    adr_text = _read(
        "docs/02-architecture/decisions/ADR-003-in-memory-locking-strategy.md"
    )
    adr_index_text = _read("docs/02-architecture/decisions/README.md")
    rules_text = _read("docs/00-project/RULES.md")

    assert "Status: Superseded (revised 2025-12-23; see ADR-010)" in adr_text
    assert "**Status:** Superseded (revised 2025-12-23; see ADR-010)" in adr_text
    assert re.search(r"ADR-003.*\|\s*Superseded\s*\|", adr_index_text)
    assert re.search(r"ADR-003.*\|\s*Superseded\s*\|", rules_text)


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

    assert "optional local-only helper stacks" in file_policy_text
    assert "canonical helper flow" in docker_quickstart_text
    assert "canonical orchestration path under ADR-010" in docker_setup_text


def test_concepts_root_surface_is_retired_from_repo_root() -> None:
    assert not (ROOT / "concepts").exists()
