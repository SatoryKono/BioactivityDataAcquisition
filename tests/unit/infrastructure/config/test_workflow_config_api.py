"""Unit tests for the canonical infrastructure workflow config API."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.application.services import RunOptions
from bioetl.domain.workflow import TransformStepConfig, WorkflowStepConfig
from bioetl.infrastructure.config import (
    load_workflow_config as public_load_workflow_config,
)
from bioetl.infrastructure.config.workflow_config_api import (
    load_workflow_config,
    resolve_workflow_config_path,
)
from bioetl.infrastructure.schemas.workflow_config import (
    RUN_OPTIONS_OVERRIDE_FIELD_NAMES,
)


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
                    "run_options": {"limit": 25},
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

    assert result == config_dir / "chembl_core.yaml"


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
    }
    assert isinstance(transform_step, TransformStepConfig)
    assert transform_step.depends_on == ("extract",)


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
    assert RUN_OPTIONS_OVERRIDE_FIELD_NAMES == {
        field.name for field in fields(RunOptions)
    }


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
