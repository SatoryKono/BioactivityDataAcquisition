"""Unit tests for the canonical infrastructure workflow config API."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import re
from typing import Any

import pytest
import yaml

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.domain.workflow import TransformStepConfig, WorkflowStepConfig
from bioetl.infrastructure.config import (
    load_workflow_config as public_load_workflow_config,
)
from bioetl.infrastructure.config.workflow_config_api import (
    load_workflow_config,
    resolve_workflow_config_dir,
    resolve_workflow_config_path,
)
from bioetl.infrastructure.schemas.workflow_config import (
    RUN_OPTIONS_OVERRIDE_FIELD_NAMES,
)

NON_COMPOSITE_ENTITY_DIR = Path("configs/entities")
WORKFLOW_CONFIG_DIR = Path("configs/workflows")
ROOT = Path(__file__).resolve().parents[4]


def _non_composite_pipeline_inventory() -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    for path in sorted(NON_COMPOSITE_ENTITY_DIR.rglob("*.yaml")):
        if "composite" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^\s*pipeline_name:\s*([\w_]+)\s*$", text, re.MULTILINE)
        assert match is not None, f"Expected pipeline_name in {path}"
        rows.append((match.group(1), path))
    return rows


def _build_workflow_payload(name: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "workflow": {
            "name": name,
            "version": "1.0.0",
            "defaults": {
                "run_options": {
                    "run_type": "backfill",
                    "dry_run": False,
                    "log_level": "DEBUG",
                }
            },
            "steps": [
                {
                    "kind": "pipeline",
                    "step_id": "extract",
                    "pipeline_name": "chembl_activity",
                    "run_options": {
                        "limit": 25,
                        "required_persistence_profile": "degraded_observable",
                    },
                },
                {
                    "kind": "transform",
                    "step_id": "normalize",
                    "transform_name": "normalize_activity_snapshot",
                    "depends_on": ["extract"],
                    "config": {"profile": "activity"},
                },
            ],
        },
    }


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)


@pytest.mark.unit
def test_resolve_workflow_config_path_uses_config_dir() -> None:
    config_dir = Path("configs/workflows")

    result = resolve_workflow_config_path("chembl_core", config_dir=config_dir)

    assert result == ROOT / "configs" / "workflows" / "chembl_core.yaml"


@pytest.mark.unit
def test_resolve_workflow_config_dir_uses_explicit_configs_root(
    tmp_path: Path,
) -> None:
    configs_root = tmp_path / "tracked-configs"

    result = resolve_workflow_config_dir(configs_root=configs_root)

    assert result == configs_root / "workflows"


@pytest.mark.unit
def test_load_workflow_config_defaults_to_repo_root_when_cwd_differs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    config = load_workflow_config("chembl_baseline")

    assert config.name == "chembl_baseline"


@pytest.mark.unit
def test_load_workflow_config_loads_defaults_and_steps(tmp_path: Path) -> None:
    workflows_dir = tmp_path / "configs" / "workflows"
    _write_yaml(
        workflows_dir / "example_activity_refresh.yaml",
        _build_workflow_payload("example_activity_refresh"),
    )

    config = load_workflow_config(
        "example_activity_refresh",
        config_dir=workflows_dir,
    )

    assert config.name == "example_activity_refresh"
    assert config.defaults.to_mapping() == {
        "run_type": "backfill",
        "dry_run": False,
        "log_level": "DEBUG",
    }
    assert len(config.steps) == 2
    pipeline_step = config.steps[0]
    transform_step = config.steps[1]
    assert isinstance(pipeline_step, WorkflowStepConfig)
    assert pipeline_step.run_options.to_mapping() == {
        "run_type": "backfill",
        "dry_run": False,
        "limit": 25,
        "log_level": "DEBUG",
        "required_persistence_profile": "degraded_observable",
    }
    assert isinstance(transform_step, TransformStepConfig)
    assert transform_step.depends_on == ("extract",)


@pytest.mark.unit
def test_load_workflow_config_accepts_full_run_options_contract(
    tmp_path: Path,
) -> None:
    workflows_dir = tmp_path / "configs" / "workflows"
    payload = _build_workflow_payload("example_activity_refresh")
    workflow_payload = payload["workflow"]
    assert isinstance(workflow_payload, dict)
    defaults_payload = workflow_payload["defaults"]
    assert isinstance(defaults_payload, dict)
    run_options_payload = defaults_payload["run_options"]
    assert isinstance(run_options_payload, dict)
    run_options_payload.update(
        {
            "debug_export_enabled": True,
            "debug_export_formats": ["csv"],
            "debug_export_dir": "artifacts/debug_exports",
            "workflow_id": "configured_workflow",
        }
    )
    _write_yaml(
        workflows_dir / "example_activity_refresh.yaml",
        payload,
    )

    config = load_workflow_config(
        "example_activity_refresh",
        config_dir=workflows_dir,
    )

    assert config.defaults.debug_export_enabled is True
    assert config.defaults.debug_export_formats == ("csv",)
    assert config.defaults.debug_export_dir == "artifacts/debug_exports"
    assert config.defaults.workflow_id == "configured_workflow"


@pytest.mark.unit
def test_load_workflow_config_preserves_composite_reconciliation_keys(
    tmp_path: Path,
) -> None:
    workflows_dir = tmp_path / "configs" / "workflows"
    payload = _build_workflow_payload("example_activity_refresh")
    workflow_payload = payload["workflow"]
    assert isinstance(workflow_payload, dict)
    steps = workflow_payload["steps"]
    assert isinstance(steps, list)
    transform_step = steps[1]
    assert isinstance(transform_step, dict)
    transform_step["config"] = {
        "source_table": "chembl_assay",
        "reference_table": "chembl_target",
        "source_keys": ["target_id", "target_type"],
        "reference_keys": ["target_id", "target_type"],
        "primary_keys": ["assay_id"],
        "action": "delete_orphans",
        "nulls_equal": True,
    }
    _write_yaml(workflows_dir / "example_activity_refresh.yaml", payload)

    config = load_workflow_config(
        "example_activity_refresh",
        config_dir=workflows_dir,
    )

    step = config.steps[1]
    assert isinstance(step, TransformStepConfig)
    assert step.config == {
        "source_table": "chembl_assay",
        "reference_table": "chembl_target",
        "source_keys": ["target_id", "target_type"],
        "reference_keys": ["target_id", "target_type"],
        "primary_keys": ["assay_id"],
        "action": "delete_orphans",
        "nulls_equal": True,
    }


@pytest.mark.unit
def test_chembl_baseline_workflow_config_declares_dependency_minimal_reconciliation_edges() -> (
    None
):
    config = load_workflow_config("chembl_baseline", config_dir=WORKFLOW_CONFIG_DIR)

    assert config.name == "chembl_baseline"
    assert config.topological_step_ids == (
        "run_chembl_assay",
        "run_chembl_target",
        "reconcile_assay_target_orphans",
        "run_chembl_publication",
        "reconcile_assay_publication_orphans",
        "reconcile_target_assay_orphans",
        "reconcile_publication_assay_orphans",
    )

    reconcile_target = config.get_step("reconcile_assay_target_orphans")
    assert isinstance(reconcile_target, TransformStepConfig)
    assert reconcile_target.depends_on == ("run_chembl_assay", "run_chembl_target")
    assert reconcile_target.config == {
        "source_layer": "gold",
        "reference_layer": "gold",
        "mutation_layer": "gold",
        "source_table": "chembl.assay",
        "reference_table": "chembl.target",
        "source_key": "target_id",
        "reference_key": "target_id",
        "primary_keys": ["assay_id"],
        "action": "delete_orphans",
        "nulls_equal": False,
    }

    reconcile_publication = config.get_step("reconcile_assay_publication_orphans")
    assert isinstance(reconcile_publication, TransformStepConfig)
    assert reconcile_publication.depends_on == (
        "reconcile_assay_target_orphans",
        "run_chembl_publication",
    )
    assert reconcile_publication.config == {
        "source_layer": "gold",
        "reference_layer": "gold",
        "mutation_layer": "gold",
        "source_table": "chembl.assay",
        "reference_table": "chembl.publication",
        "source_key": "publication_id",
        "reference_key": "publication_id",
        "primary_keys": ["assay_id"],
        "action": "delete_orphans",
        "nulls_equal": False,
    }

    reconcile_target_inverse = config.get_step("reconcile_target_assay_orphans")
    assert isinstance(reconcile_target_inverse, TransformStepConfig)
    assert reconcile_target_inverse.depends_on == (
        "reconcile_assay_publication_orphans",
    )
    assert reconcile_target_inverse.config == {
        "source_layer": "gold",
        "reference_layer": "gold",
        "mutation_layer": "gold",
        "source_table": "chembl.target",
        "reference_table": "chembl.assay",
        "source_key": "target_id",
        "reference_key": "target_id",
        "primary_keys": ["target_id"],
        "action": "delete_orphans",
        "nulls_equal": False,
    }

    reconcile_publication_inverse = config.get_step(
        "reconcile_publication_assay_orphans"
    )
    assert isinstance(reconcile_publication_inverse, TransformStepConfig)
    assert reconcile_publication_inverse.depends_on == (
        "reconcile_target_assay_orphans",
    )
    assert reconcile_publication_inverse.config == {
        "source_layer": "gold",
        "reference_layer": "gold",
        "mutation_layer": "gold",
        "source_table": "chembl.publication",
        "reference_table": "chembl.assay",
        "source_key": "publication_id",
        "reference_key": "publication_id",
        "primary_keys": ["publication_id"],
        "action": "delete_orphans",
        "nulls_equal": False,
    }


@pytest.mark.unit
def test_load_workflow_config_rejects_unknown_run_options(tmp_path: Path) -> None:
    workflows_dir = tmp_path / "configs" / "workflows"
    payload = _build_workflow_payload("example_activity_refresh")
    workflow_payload = payload["workflow"]
    assert isinstance(workflow_payload, dict)
    steps = workflow_payload["steps"]
    assert isinstance(steps, list)
    first_step = steps[0]
    assert isinstance(first_step, dict)
    run_options = first_step["run_options"]
    assert isinstance(run_options, dict)
    run_options["unknown_flag"] = True
    _write_yaml(workflows_dir / "example_activity_refresh.yaml", payload)

    with pytest.raises(ValueError, match="unknown_flag"):
        load_workflow_config(
            "example_activity_refresh",
            config_dir=workflows_dir,
        )


@pytest.mark.unit
def test_workflow_run_options_whitelist_matches_application_run_options() -> None:
    internal_correlation_fields = {
        "workflow_name",
        "workflow_run_id",
        "workflow_step_id",
    }
    assert (
        RUN_OPTIONS_OVERRIDE_FIELD_NAMES
        == {field.name for field in fields(RunOptions)} - internal_correlation_fields
    )


@pytest.mark.unit
def test_public_config_package_reexports_load_workflow_config(tmp_path: Path) -> None:
    workflows_dir = tmp_path / "configs" / "workflows"
    _write_yaml(
        workflows_dir / "example_activity_refresh.yaml",
        _build_workflow_payload("example_activity_refresh"),
    )

    config = public_load_workflow_config(
        "example_activity_refresh",
        config_dir=workflows_dir,
    )

    assert public_load_workflow_config is load_workflow_config
    assert config.name == "example_activity_refresh"


@pytest.mark.unit
def test_every_non_composite_pipeline_has_matching_workflow_wrapper() -> None:
    for pipeline_name, _config_path in _non_composite_pipeline_inventory():
        wrapper_path = WORKFLOW_CONFIG_DIR / f"{pipeline_name}.yaml"
        assert wrapper_path.exists(), (
            "Every non-composite pipeline must publish a matching workflow wrapper: "
            f"missing {wrapper_path}"
        )


@pytest.mark.unit
def test_single_pipeline_workflow_wrappers_load_and_match_identity() -> None:
    for pipeline_name, _config_path in _non_composite_pipeline_inventory():
        config = load_workflow_config(pipeline_name, config_dir=WORKFLOW_CONFIG_DIR)
        assert config.name == pipeline_name
        if pipeline_name == "chembl_target_protein_classification":
            assert tuple(step.step_id for step in config.steps) == (
                "run_chembl_target",
                "run_chembl_target_component",
                "run_chembl_protein_class",
                "run_chembl_target_protein_classification",
            )
            continue
        assert len(config.steps) == 1
        step = config.steps[0]
        assert isinstance(step, WorkflowStepConfig)
        assert step.step_id == f"run_{pipeline_name}"
        assert step.pipeline_name == pipeline_name
        assert step.depends_on == ()


@pytest.mark.unit
def test_all_shipped_workflow_configs_load_successfully() -> None:
    for path in sorted(WORKFLOW_CONFIG_DIR.glob("*.yaml")):
        config = load_workflow_config(path.stem, config_dir=WORKFLOW_CONFIG_DIR)
        assert config.name == path.stem


@pytest.mark.unit
def test_provider_pack_workflows_are_additive_multi_step_configs() -> None:
    expected_steps = {
        "chembl_reference_pack": 10,
        "publication_provider_pack": 4,
        "uniprot_support_pack": 2,
    }
    for workflow_name, step_count in expected_steps.items():
        config = load_workflow_config(workflow_name, config_dir=WORKFLOW_CONFIG_DIR)
        assert config.name == workflow_name
        assert len(config.steps) == step_count
