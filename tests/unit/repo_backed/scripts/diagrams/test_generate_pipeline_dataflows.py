# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Repo-backed tests for source-driven pipeline dataflow documentation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.diagrams import __main__ as diagrams_router
from scripts.diagrams import pipeline_dataflow_ir
from scripts.diagrams.generate_pipeline_dataflows import main
from scripts.diagrams.pipeline_dataflow_ir import (
    PipelineDataflowIR,
    build_pipeline_dataflow_ir,
)
from scripts.diagrams.pipeline_dataflow_render import (
    DIAGRAM_FILENAMES,
    render_mermaid_views,
)
from scripts.schema.generate_unified_schema_map import build_unified_schema_rows

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

REPO_ROOT = Path(__file__).resolve().parents[5]


def test_source_date_uses_pr_head_parent_without_merge_commit_entropy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def _run(args: list[str], **_: object) -> SimpleNamespace:
        calls.append(args)
        return SimpleNamespace(stdout="2026-07-30\n")

    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setattr(pipeline_dataflow_ir.subprocess, "run", _run)

    assert pipeline_dataflow_ir._source_date() == "2026-07-30"
    assert calls == [
        [
            "git",
            "log",
            "--no-merges",
            "-1",
            "--format=%cs",
            "HEAD^2",
            "--",
            "configs",
            "src/bioetl",
        ]
    ]


@pytest.fixture(scope="module")
def activity_ir() -> PipelineDataflowIR:
    return build_pipeline_dataflow_ir(
        "chembl_activity",
        configs_root=REPO_ROOT / "configs",
    )


def test_ir_resolves_effective_chembl_activity_policy(
    activity_ir: PipelineDataflowIR,
) -> None:
    extraction = {
        item.source_key: item.value for item in activity_ir.extraction_criteria
    }

    assert extraction == {
        "standard_type__in": "IC50,Ki",
        "standard_units": "nM",
        "standard_relation": "=",
        "assay_type__in": "B,F",
        "potential_duplicate": 0,
        "data_validity_comment__isnull": True,
        "pchembl_value__isnull": False,
        "standard_flag": 1,
        "target_tax_id__isnull": False,
    }
    assert activity_ir.input_criteria[0].enabled is False
    assert len(activity_ir.silver_criteria) == 29
    assert len(activity_ir.gold_criteria) == 13
    assert len(activity_ir.dq.field_validations) == 29
    assert len(activity_ir.dq.cross_field_validations) == 6
    assert len(activity_ir.dq.conditional_validations) == 6
    assert activity_ir.post_processing.code_defined_methods == (
        "_postprocess_pre_silver_record",
        "transform_for_gold",
    )


def test_ir_lists_actual_silver_and_gold_projections(
    activity_ir: PipelineDataflowIR,
) -> None:
    silver_names = [field.name for field in activity_ir.silver.fields]
    gold_names = [field.name for field in activity_ir.gold.fields]

    assert len(silver_names) == 77
    assert silver_names[:3] == ["entity_id", "content_hash", "_run_id"]
    assert silver_names[-2:] == ["_dq_error", "_dq_warn"]
    assert len(gold_names) == 66
    assert gold_names[:3] == ["entity_id", "content_hash", "activity_id"]
    assert activity_ir.gold.contract_field_count == 72
    assert activity_ir.gold.omitted_contract_fields == (
        "_dq_error",
        "_dq_warn",
        "_index",
        "relation",
        "type",
        "value",
    )
    assert {item.code for item in activity_ir.diagnostics} == {
        "GOLD_CONTRACT_FIELDS_EXCLUDED_BY_POLICY",
        "GOLD_CONTRACT_FIELDS_NOT_SELECTED_BY_GROUPS",
    }


def test_mermaid_views_cover_all_fields_without_oversized_nodes(
    activity_ir: PipelineDataflowIR,
) -> None:
    views = render_mermaid_views(activity_ir)

    assert tuple(views) == DIAGRAM_FILENAMES
    criteria_source = views[DIAGRAM_FILENAMES[1]]
    assert "classDef criteriaCard font-size:14px" in criteria_source
    assert "activity_id range [1.0, 10000000000.0]" in criteria_source
    assert "data_validity_comment exclude if present" in criteria_source
    expected_sheets = (
        activity_ir.silver.fields[:60],
        activity_ir.silver.fields[60:],
        activity_ir.gold.fields[:60],
        activity_ir.gold.fields[60:],
    )
    for filename, expected_fields in zip(
        DIAGRAM_FILENAMES[2:], expected_sheets, strict=True
    ):
        source = views[filename]
        assert "flowchart TB" in source
        assert "'wrappingWidth': 360" in source
        assert source.count("    Layer -->") == 2
        assert "classDef fieldCard font-size:13px" in source
        assert all(f"<br/>{field.name}" in source for field in expected_fields)
        field_nodes = [
            line for line in source.splitlines() if "Fields" in line and '["' in line
        ]
        assert all(line.count("<br/>") <= 5 for line in field_nodes)


def test_cli_generation_and_drift_check(tmp_path: Path) -> None:
    diagram_dir = tmp_path / "architecture"
    description_dir = tmp_path / "descriptions"
    artifact_root = tmp_path / "generated"
    args = [
        "--pipeline",
        "chembl_activity",
        "--configs-root",
        str(REPO_ROOT / "configs"),
        "--diagram-dir",
        str(diagram_dir),
        "--description-dir",
        str(description_dir),
        "--artifact-root",
        str(artifact_root),
    ]

    assert main(args) == 0
    assert main([*args, "--check"]) == 0

    stale_path = diagram_dir / DIAGRAM_FILENAMES[0]
    stale_path.write_text("stale\n", encoding="utf-8")
    assert main([*args, "--check"]) == 1


def test_router_exposes_module_based_generator() -> None:
    command = diagrams_router.COMMAND_SPECS["generate-dataflows"]

    assert command.runner == "module"
    assert command.target == "scripts.diagrams.generate_pipeline_dataflows"


def test_unified_schema_inventory_ignores_composite_workflow_configs() -> None:
    rows = build_unified_schema_rows()

    assert rows
    assert any(row["pipeline_name"] == "chembl_activity" for row in rows)
    assert all("/composite/" not in row["config_path"] for row in rows)


def test_cli_reports_controlled_build_failure(monkeypatch) -> None:
    def boom(_args):
        raise ValueError("simulated build failure")

    monkeypatch.setattr(
        "scripts.diagrams.generate_pipeline_dataflows.build_outputs",
        boom,
    )
    assert main(["--pipeline", "chembl_activity"]) == 1


def test_project_fields_rejects_unknown_groups() -> None:
    from scripts.diagrams.pipeline_dataflow_ir import _project_fields

    with pytest.raises(ValueError, match="Unknown column groups"):
        _project_fields(
            ["a", "b"],
            groups=[{"name": "core", "fields": ["a"]}],
            include_groups=["missing_group"],
            exclude_fields=[],
        )


def test_project_fields_follows_column_groups_order() -> None:
    from scripts.diagrams.pipeline_dataflow_ir import _project_fields

    result = _project_fields(
        ["a", "b", "c"],
        groups=[
            {"name": "second", "fields": ["b"]},
            {"name": "first", "fields": ["a"]},
            {"name": "third", "fields": ["c"]},
        ],
        include_groups=["third", "first"],
        exclude_fields=[],
    )
    # Runtime preserves column_groups order: first appears before third in groups list.
    assert result == ["a", "c"]


def test_transformer_registry_lookup_via_ast(activity_ir: PipelineDataflowIR) -> None:
    transformer = activity_ir.post_processing.transformer_class
    assert transformer
    assert "Activity" in transformer or "activity" in transformer.lower()


def test_overview_and_criteria_render_input_filter_from_ir(
    activity_ir: PipelineDataflowIR,
) -> None:
    views = render_mermaid_views(activity_ir)
    overview = views[DIAGRAM_FILENAMES[0]]
    criteria = views[DIAGRAM_FILENAMES[1]]
    assert "Input-file filter<br/>disabled" in overview
    assert "enabled = false" in criteria
    assert "class SilverExclude warning" in criteria
