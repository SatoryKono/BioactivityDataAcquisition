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
"""Regression checks for critical declared-vs-emitted observability families."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa import report_observability_metric_inventory as inventory


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


def test_critical_observability_metric_families_are_runtime_emitted() -> None:
    report = inventory.collect_metric_inventory(ROOT)

    emitted_metrics = set(report["emitted_metrics"])
    critical_families = {
        "bioetl_control_plane_manifest_writes_total",
        "bioetl_control_plane_ledger_appends_total",
        "bioetl_checkpoint_compatibility_events_total",
        "bioetl_replay_drift_events_total",
        "bioetl_replay_lag_seconds",
        "bioetl_replay_reconstructability_events_total",
        "bioetl_record_flow_invariants_total",
        "bioetl_stage_backlog_records",
        "bioetl_stage_lag_seconds",
        "bioetl_postrun_phase_events_total",
        "bioetl_postrun_phase_duration_seconds",
        "bioetl_metrics_publication_events_total",
    }

    missing = sorted(critical_families - emitted_metrics)
    assert not missing, (
        "Critical observability metric families must be emitted on runtime paths: "
        f"{missing}"
    )


def test_critical_observability_metric_families_have_runtime_emitters() -> None:
    report = inventory.collect_metric_inventory(ROOT)
    runtime_emitters = {
        **report["runtime_emitters"],
        **report["helper_backed_emitters"],
    }
    expectations = {
        "bioetl_control_plane_manifest_writes_total": "src/bioetl/infrastructure/control_plane",
        "bioetl_control_plane_ledger_appends_total": "src/bioetl/infrastructure/control_plane",
        "bioetl_checkpoint_compatibility_events_total": "src/bioetl/application",
        "bioetl_replay_reconstructability_events_total": (
            "src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py"
        ),
        "bioetl_replay_drift_events_total": (
            "src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py"
        ),
        "bioetl_replay_lag_seconds": (
            "src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py"
        ),
        "bioetl_record_flow_invariants_total": "src/bioetl/application",
        "bioetl_stage_backlog_records": "src/bioetl/application",
        "bioetl_stage_lag_seconds": "src/bioetl/application",
        "bioetl_postrun_phase_events_total": "src/bioetl/application/core/postrun",
        "bioetl_postrun_phase_duration_seconds": "src/bioetl/application/core/postrun",
        "bioetl_metrics_publication_events_total": "src/bioetl/infrastructure/observability/server.py",
    }

    missing: list[str] = []
    for metric_name, expected_path_fragment in expectations.items():
        emitters = runtime_emitters.get(metric_name, [])
        if not any(expected_path_fragment in path for path in emitters):
            missing.append(f"{metric_name} -> {emitters}")

    assert not missing, (
        "Critical observability families must stay backed by expected runtime "
        f"emitters: {missing}"
    )


def test_direct_runtime_metric_emitters_match_declared_label_contracts() -> None:
    report = inventory.collect_metric_inventory(ROOT)

    assert report["runtime_label_contract_violations"] == []
