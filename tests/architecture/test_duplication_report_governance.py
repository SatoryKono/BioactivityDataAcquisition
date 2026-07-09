from __future__ import annotations

import pytest

import json
from pathlib import Path

from scripts.engineering.qa.report_duplication_baseline import DuplicateCluster
from scripts.engineering.qa.report_duplication_baseline import DuplicateModuleRef
from scripts.engineering.qa.report_duplication_baseline import TargetDuplicationReport
from scripts.engineering.qa.report_duplication_baseline import _render_markdown

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOTSPOT_BASELINE_JSON = (
    PROJECT_ROOT / "reports/quality/hotspot-duplication-baseline.json"
)
SPECIALIZED_DUPLICATION_ARTIFACTS = (
    {
        "name": "control-plane",
        "target": "src/bioetl/application/services/control_plane",
        "json_path": PROJECT_ROOT / "reports/quality/control-plane-duplication.json",
        "md_path": PROJECT_ROOT / "reports/quality/control-plane-duplication.md",
    },
    {
        "name": "runtime-builders",
        "target": "src/bioetl/composition/runtime_builders",
        "json_path": PROJECT_ROOT / "reports/quality/runtime-builders-duplication.json",
        "md_path": PROJECT_ROOT / "reports/quality/runtime-builders-duplication.md",
    },
)
FULL_APP_DUPLICATION_ARTIFACT = {
    "json_path": PROJECT_ROOT / "reports/quality/full-app-duplication-baseline.json",
    "md_path": PROJECT_ROOT / "reports/quality/full-app-duplication-baseline.md",
    "targets": {
        "src/bioetl/infrastructure/adapters",
        "src/bioetl/application/pipelines",
        "src/bioetl/composition/bootstrap",
        "src/bioetl/interfaces/cli",
    },
}


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _target_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = payload.get("targets", [])
    assert isinstance(rows, list)
    return [row for row in rows if isinstance(row, dict)]


def _single_report_from_payload(payload: dict[str, object]) -> TargetDuplicationReport:
    target_rows = _target_rows(payload)
    assert len(target_rows) == 1
    row = target_rows[0]

    clusters_payload = row.get("clusters", [])
    assert isinstance(clusters_payload, list)
    clusters: list[DuplicateCluster] = []
    for cluster_payload in clusters_payload:
        assert isinstance(cluster_payload, dict)
        modules_payload = cluster_payload.get("modules", [])
        assert isinstance(modules_payload, list)
        modules = []
        for module_payload in modules_payload:
            assert isinstance(module_payload, dict)
            module = module_payload.get("module")
            start_line = module_payload.get("start_line")
            end_line = module_payload.get("end_line")
            assert isinstance(module, str)
            assert isinstance(start_line, int)
            assert isinstance(end_line, int)
            modules.append(
                DuplicateModuleRef(
                    module=module,
                    start_line=start_line,
                    end_line=end_line,
                )
            )
        path = cluster_payload.get("path")
        line = cluster_payload.get("line")
        assert isinstance(path, str)
        assert isinstance(line, int)
        clusters.append(
            DuplicateCluster(
                path=path,
                line=line,
                modules=tuple(modules),
            )
        )

    target = row.get("target")
    returncode = row.get("returncode")
    duplicate_count = row.get("duplicate_count")
    raw_duplicate_count = row.get("raw_duplicate_count")
    assert isinstance(target, str)
    assert isinstance(returncode, int)
    assert isinstance(duplicate_count, int)
    assert isinstance(raw_duplicate_count, int)
    return TargetDuplicationReport(
        target=target,
        returncode=returncode,
        duplicate_count=duplicate_count,
        raw_duplicate_count=raw_duplicate_count,
        clusters=tuple(clusters),
    )


def _reports_from_payload(payload: dict[str, object]) -> list[TargetDuplicationReport]:
    reports: list[TargetDuplicationReport] = []
    for row in _target_rows(payload):
        single_payload = {**payload, "targets": [row]}
        reports.append(_single_report_from_payload(single_payload))
    return reports


def test_specialized_duplication_reports_match_hotspot_baseline_targets() -> None:
    hotspot_payload = _load_json(HOTSPOT_BASELINE_JSON)
    hotspot_targets = {
        row["target"]: row
        for row in _target_rows(hotspot_payload)
        if isinstance(row.get("target"), str)
    }
    hotspot_normalization = hotspot_payload.get("normalization", {})
    assert isinstance(hotspot_normalization, dict)

    for artifact in SPECIALIZED_DUPLICATION_ARTIFACTS:
        payload = _load_json(artifact["json_path"])
        summary = payload.get("summary", {})
        assert isinstance(summary, dict)
        assert summary.get("targets") == 1

        normalization = payload.get("normalization", {})
        assert isinstance(normalization, dict)
        assert normalization == hotspot_normalization

        target_rows = _target_rows(payload)
        assert len(target_rows) == 1
        target_row = target_rows[0]
        assert target_row.get("target") == artifact["target"]
        assert summary.get("total_duplicate_clusters") == target_row.get(
            "duplicate_count"
        )
        assert artifact["target"] in hotspot_targets
        hotspot_row = hotspot_targets[artifact["target"]]
        for key in (
            "target",
            "returncode",
            "duplicate_count",
            "raw_duplicate_count",
            "excluded_duplicate_count",
            "top_pairs",
            "clusters",
        ):
            assert target_row.get(key) == hotspot_row.get(key), (
                f"{artifact['name']} duplication artifact drifted from the canonical "
                f"hotspot baseline for {artifact['target']}."
            )


def test_specialized_duplication_markdown_matches_json_payload() -> None:
    for artifact in SPECIALIZED_DUPLICATION_ARTIFACTS:
        payload = _load_json(artifact["json_path"])
        normalization = payload.get("normalization", {})
        assert isinstance(normalization, dict)
        exclude_patterns = normalization.get("exclude_module_patterns", [])
        assert isinstance(exclude_patterns, list)

        expected_markdown = _render_markdown(
            [_single_report_from_payload(payload)],
            exclude_module_patterns=tuple(
                pattern for pattern in exclude_patterns if isinstance(pattern, str)
            ),
            exclude_actionability_categories=tuple(
                category
                for category in normalization.get(
                    "exclude_actionability_categories", []
                )
                if isinstance(category, str)
            ),
            trend_summary=payload.get("trend")
            if isinstance(payload.get("trend"), dict)
            else None,
        )
        actual_markdown = artifact["md_path"].read_text(encoding="utf-8")
        assert actual_markdown == expected_markdown, (
            f"{artifact['name']} duplication markdown artifact is out of sync with "
            f"{artifact['json_path'].relative_to(PROJECT_ROOT)}."
        )


def test_hotspot_duplication_baseline_is_clean_zero_ratchet() -> None:
    payload = _load_json(HOTSPOT_BASELINE_JSON)
    summary = payload.get("summary", {})
    assert isinstance(summary, dict)

    assert summary.get("total_duplicate_clusters") == 0
    assert summary.get("total_raw_duplicate_clusters") == 0


def test_full_app_duplication_baseline_covers_audit_visibility_scope() -> None:
    payload = _load_json(FULL_APP_DUPLICATION_ARTIFACT["json_path"])
    summary = payload.get("summary", {})
    assert isinstance(summary, dict)
    rows = _target_rows(payload)

    assert summary.get("targets") == len(FULL_APP_DUPLICATION_ARTIFACT["targets"])
    assert {row["target"] for row in rows} == FULL_APP_DUPLICATION_ARTIFACT["targets"]
    assert summary["total_duplicate_clusters"] == sum(
        int(row["duplicate_count"]) for row in rows
    )
    assert summary["total_raw_duplicate_clusters"] == sum(
        int(row["raw_duplicate_count"]) for row in rows
    )
    assert payload.get("trend") == {
        "status": "no_prior_snapshot",
        "snapshot_date": summary["snapshot_date"],
    }
    ranking = payload.get("reduction_leverage_ranking")
    assert isinstance(ranking, list) and ranking
    first_wave = payload.get("first_wave")
    assert isinstance(first_wave, dict)
    assert first_wave.get("status") == "selected"
    assert first_wave.get("target") in FULL_APP_DUPLICATION_ARTIFACT["targets"]


def test_issue_5486_cli_first_wave_reduces_reviewed_duplication_leverage() -> None:
    """Issue #5486 keeps reviewed CLI duplication burned down and reclassified."""
    payload = _load_json(FULL_APP_DUPLICATION_ARTIFACT["json_path"])
    rows = {
        row["target"]: row
        for row in _target_rows(payload)
        if isinstance(row.get("target"), str)
    }
    cli_row = rows["src/bioetl/interfaces/cli"]

    assert cli_row["duplicate_count"] <= 12
    assert cli_row["raw_duplicate_count"] <= 12
    assert cli_row["excluded_duplicate_count"] == 0
    assert cli_row["actionability"] == [
        {
            "category": "cli_command_contract_shell",
            "duplicate_clusters": cli_row["duplicate_count"],
        }
    ]

    ranking = payload.get("reduction_leverage_ranking")
    assert isinstance(ranking, list) and ranking
    cli_ranking_row = next(
        row
        for row in ranking
        if isinstance(row, dict) and row.get("target") == "src/bioetl/interfaces/cli"
    )
    assert cli_ranking_row == {
        "target": "src/bioetl/interfaces/cli",
        "duplicate_clusters": cli_row["duplicate_count"],
        "dominant_actionability_category": "cli_command_contract_shell",
        "dominant_actionability_cluster_count": cli_row["duplicate_count"],
        "low_risk_cluster_count": cli_row["duplicate_count"],
        "low_risk_cluster_share": 0.0,
        "recommended_first_wave": False,
    }

    first_wave = payload.get("first_wave")
    assert isinstance(first_wave, dict)
    assert first_wave["target"] != "src/bioetl/interfaces/cli"
    assert first_wave["duplicate_clusters"] >= cli_row["duplicate_count"]


def test_full_app_duplication_markdown_matches_json_payload() -> None:
    payload = _load_json(FULL_APP_DUPLICATION_ARTIFACT["json_path"])
    normalization = payload.get("normalization", {})
    assert isinstance(normalization, dict)
    exclude_patterns = normalization.get("exclude_module_patterns", [])
    assert isinstance(exclude_patterns, list)

    expected_markdown = _render_markdown(
        _reports_from_payload(payload),
        exclude_module_patterns=tuple(
            pattern for pattern in exclude_patterns if isinstance(pattern, str)
        ),
        exclude_actionability_categories=tuple(
            category
            for category in normalization.get("exclude_actionability_categories", [])
            if isinstance(category, str)
        ),
        trend_summary=payload.get("trend")
        if isinstance(payload.get("trend"), dict)
        else None,
    )
    actual_markdown = FULL_APP_DUPLICATION_ARTIFACT["md_path"].read_text(
        encoding="utf-8"
    )
    assert actual_markdown == expected_markdown
