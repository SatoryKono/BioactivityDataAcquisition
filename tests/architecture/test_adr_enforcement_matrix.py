# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guards for accepted ADR enforcement coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa import report_adr_enforcement_matrix as adr_matrix
from scripts.engineering.qa.report_adr_enforcement_matrix import build_payload

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "reports" / "quality" / "adr-enforcement-matrix.json"

pytestmark = pytest.mark.architecture

LEGACY_ADR_ENFORCEMENT_ANCHORS = {
    "ADR-004": (
        "docs/00-project/RULES.md",
        "tests/unit/domain/entities/test_pydantic_dtos.py",
    ),
    "ADR-009": (
        "docs/00-project/RULES.md",
        "tests/unit/infrastructure/adapters/http/test_pagination.py",
    ),
    "ADR-011": (
        "docs/00-project/RULES.md",
        "tests/architecture/test_config_surface_entity_residual_plateau.py",
    ),
    "ADR-012": (
        "docs/03-guides/pipeline-lifecycle.md",
        "tests/integration/test_runner_lifecycle.py",
    ),
    "ADR-013": (
        "docs/03-guides/pipeline-lifecycle.md",
        "tests/integration/infrastructure/storage/test_bronze_writer_cleanup.py",
    ),
    "ADR-015": (
        "docs/03-guides/pipeline-lifecycle.md",
        "tests/unit/application/core/test_pipeline_services.py",
    ),
    "ADR-016": (
        "docs/00-project/RULES.md",
        "tests/unit/application/services/test_error_handler.py",
    ),
    "ADR-019": (
        "docs/03-guides/metrics-monitoring.md",
        "tests/unit/infrastructure/observability/test_metrics_port_contract.py",
    ),
    "ADR-020": (
        "src/bioetl/application/core/pipeline_services.py",
        "tests/architecture/test_base_pipeline_purity.py",
    ),
    "ADR-021": (
        "docs/04-reference/domain/aggregates.md",
        "tests/unit/domain/aggregates/test_pipeline_run.py",
    ),
    "ADR-022": (
        "src/bioetl/infrastructure/observability/tracing.py",
        "tests/architecture/test_tracing_enforcement.py",
    ),
    "ADR-023": (
        "docs/00-project/RULES.md",
        "tests/architecture/test_entity_pipeline_intentional_overrides.py",
    ),
    "ADR-030": (
        "src/bioetl/application/pipelines/chembl/pipeline_types.py",
        "tests/unit/application/pipelines/test_page_parsing.py",
    ),
    "ADR-032": (
        "docs/00-project/RULES.md",
        "tests/integration/adapters/test_http_retry_semantics.py",
    ),
    "ADR-038": (
        "configs/naming_exceptions.yaml",
        "tests/contract/test_chembl_enum_normalization_policy.py",
    ),
    "ADR-051": (
        "configs/quality/constructor_waivers.yaml",
        "tests/unit/domain/aggregates/test_quarantine_entry.py",
    ),
    "ADR-053": (
        "docs/03-guides/dashboards/dashboard-system-2.0-phase2-residual.md",
        "scripts/engineering/qa/check_dashboard_visual_semantics.py",
    ),
}


def _matrix_drift_report(committed: dict[str, object], live: dict[str, object]) -> str:
    """Build a compact drift report for the ADR enforcement matrix artifact."""
    committed_rows = {
        str(row["adr_id"]): row
        for row in committed.get("rows", [])  # type: ignore[union-attr]
        if isinstance(row, dict) and "adr_id" in row
    }
    live_rows = {
        str(row["adr_id"]): row
        for row in live.get("rows", [])  # type: ignore[union-attr]
        if isinstance(row, dict) and "adr_id" in row
    }
    only_committed = sorted(set(committed_rows) - set(live_rows))
    only_live = sorted(set(live_rows) - set(committed_rows))
    changed = sorted(
        adr_id
        for adr_id in set(committed_rows) & set(live_rows)
        if committed_rows[adr_id] != live_rows[adr_id]
    )
    lines = [
        "ADR enforcement matrix artifact is stale relative to live generator.",
        f"committed.summary={committed.get('summary')!r}",
        f"live.summary={live.get('summary')!r}",
        f"only_in_artifact={only_committed}",
        f"only_in_live={only_live}",
        f"changed_rows={changed[:20]}{'...' if len(changed) > 20 else ''}",
        "Refresh with:",
        "  python -m scripts.engineering.qa.report_adr_enforcement_matrix --update",
    ]
    return "\n".join(lines)


def test_adr_enforcement_matrix_artifact_matches_live_generator() -> None:
    assert ARTIFACT.exists()

    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    live = build_payload(repo_root=ROOT)

    if committed != live:
        raise AssertionError(_matrix_drift_report(committed, live))


def test_accepted_adr_enforcement_matrix_has_no_unreviewed_gaps() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert payload["summary"]["blocking_gap_count"] == 0
    assert payload["summary"]["missing_enforcement_owner_count"] == 0


def test_legacy_adr_enforcement_anchor_paths_exist() -> None:
    for adr_id, anchor_paths in LEGACY_ADR_ENFORCEMENT_ANCHORS.items():
        assert adr_id.startswith("ADR-")
        for rel_path in anchor_paths:
            assert (ROOT / rel_path).exists(), f"{adr_id} anchor missing: {rel_path}"


def test_adr_reference_index_uses_python_fallback_when_git_grep_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(adr_matrix, "_git_grep_reference_lines", lambda repo_root: None)
    monkeypatch.setattr(adr_matrix, "_ripgrep_reference_lines", lambda repo_root: None)
    monkeypatch.setattr(
        adr_matrix.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("Python ADR fallback must not call Git"),
    )

    docs_path = tmp_path / "docs" / "00-project" / "RULES.md"
    docs_path.parent.mkdir(parents=True)
    docs_path.write_text("Accepted decision ADR-004.\n", encoding="utf-8")
    tests_path = tmp_path / "tests" / "test_adr_guard.py"
    tests_path.parent.mkdir(parents=True)
    tests_path.write_text("def test_guard():\n    assert 'ADR-004'\n", encoding="utf-8")

    reference_paths_by_adr, manual_exceptions = adr_matrix._reference_index(tmp_path)

    assert reference_paths_by_adr["ADR-004"] == {
        "docs/00-project/RULES.md",
        "tests/test_adr_guard.py",
    }
    assert isinstance(manual_exceptions, dict)
