"""Regression checks for fail-closed live acceptance."""

from __future__ import annotations

import pytest
import json
from pathlib import Path

from scripts.ops.observability.green_acceptance import Case, command, green_failures


pytestmark = pytest.mark.unit


def test_composite_children_cannot_substitute_parent_evidence(tmp_path):
    from scripts.ops.observability.green_acceptance import inspect_composite_parents

    folder = tmp_path / "output/control/run_manifest"
    folder.mkdir(parents=True)
    (folder / "parent.json").write_text(
        json.dumps(
            {
                "provider": "composite",
                "pipeline_name": "composite_activity",
                "run_id": "parent",
            }
        )
    )
    failures = inspect_composite_parents(
        Case("composite", "composite_activity"),
        tmp_path,
        [tmp_path / "pipeline/chembl_activity/child/pipeline-run-report.json"],
    )
    assert failures == ["composite_parent_report_missing:composite_activity"]


def test_matrix_covers_every_case_and_prepares_derived_inputs():
    from scripts.ops.observability.green_acceptance import discover

    root = Path(__file__).resolve().parents[5]
    cases = discover(root)
    assert len(cases) == 54
    target = next(
        case
        for case in cases
        if case.id == "pipeline-chembl_target_protein_classification"
    )
    assert set(target.prerequisites) == {
        "chembl_target",
        "chembl_target_component",
        "chembl_protein_class",
    }
    for prerequisite in target.prerequisites:
        args = command(Case("pipeline", prerequisite))
        assert args[args.index("--limit") + 1] == "1000"


def test_error_log_cannot_be_hidden_by_successful_exit():
    from scripts.ops.observability.green_acceptance import logged_errors

    assert logged_errors('{"level":"error","event":"write_failed"}') == [
        "error_log:write_failed"
    ]
    assert logged_errors('{"level":"info","event":"completed"}') == []


def test_composite_limit_alias_preserves_seed_limit():
    from bioetl.interfaces.cli.commands.run_composite import run_composite

    option = next(param for param in run_composite.params if param.name == "seed_limit")
    assert {"--seed-limit", "--limit"} <= set(option.opts)


@pytest.mark.parametrize("kind", ["pipeline", "workflow", "composite"])
def test_every_launch_has_limit_1000(kind):
    args = command(Case(kind, "chembl_assay"))
    assert args[args.index("--limit") + 1] == "1000"
    assert (
        args[args.index("--required-persistence-profile") + 1] == "degraded_observable"
    )


def test_all_green_passes():
    assert (
        green_failures(
            "success",
            {"saved_evidence_status": "OK", "replay_readiness_status": "OK"},
            {"verdict": "OK", "evidence_completeness": "COMPLETE"},
        )
        == []
    )


@pytest.mark.parametrize(
    "value", [None, "UNKNOWN", "INCOMPLETE", "N/A", "WARN", "ERROR", "QUERY ERROR"]
)
@pytest.mark.parametrize("field", ["saved_evidence_status", "replay_readiness_status"])
def test_non_green_evidence_fails(field, value):
    presentation = {
        "saved_evidence_status": "OK",
        "replay_readiness_status": "OK",
        field: value,
    }
    assert green_failures(
        "success", presentation, {"verdict": "OK", "evidence_completeness": "COMPLETE"}
    )


@pytest.mark.parametrize(
    "status", ["failed", "running", "partial", "shutdown", "unknown"]
)
def test_failed_execution_cannot_be_hidden_by_green_evidence(status):
    assert green_failures(
        status,
        {"saved_evidence_status": "OK", "replay_readiness_status": "OK"},
        {"verdict": "OK", "evidence_completeness": "COMPLETE"},
    )
