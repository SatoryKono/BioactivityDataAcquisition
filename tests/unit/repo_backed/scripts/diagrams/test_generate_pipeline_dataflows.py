"""Repo-backed tests for source-driven pipeline dataflow documentation."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.diagrams import __main__ as diagrams_router
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
