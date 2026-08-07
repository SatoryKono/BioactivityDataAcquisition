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
"""Integration regression tests for the canonical config validator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

pytestmark = pytest.mark.integration


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    module_path = (
        repo_root / "scripts" / "schema" / "validation" / "validate_pipeline_configs.py"
    )
    spec = importlib.util.spec_from_file_location(
        "validate_pipeline_configs_module",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _copy_repo_file(tmp_path: Path, relative_path: str) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    source = repo_root / relative_path
    target = tmp_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _build_minimal_crossref_tree(tmp_path: Path) -> Path:
    for relative_path in (
        "configs/_schema/pipeline.json",
        "configs/_schema/composite.json",
        "configs/base/pipeline.yaml",
        "configs/entities/crossref/publication.yaml",
        "configs/providers/crossref.yaml",
        "configs/workflows/crossref_publication.yaml",
    ):
        _copy_repo_file(tmp_path, relative_path)
    return tmp_path / "configs"


def test_validate_config_tree_reports_missing_workflow_pipeline_reference(
    tmp_path: Path,
) -> None:
    module = _load_module()
    configs_root = _build_minimal_crossref_tree(tmp_path)

    workflow_path = configs_root / "workflows" / "crossref_publication.yaml"
    workflow_payload = _load_yaml(workflow_path)
    workflow = workflow_payload["workflow"]
    assert isinstance(workflow, dict)
    steps = workflow["steps"]
    assert isinstance(steps, list) and steps
    first_step = steps[0]
    assert isinstance(first_step, dict)
    first_step["pipeline_name"] = "missing_publication"
    _write_yaml(workflow_path, workflow_payload)

    errors, warnings, total = module.validate_config_tree(configs_root)

    assert total == 3
    assert not warnings
    assert any(
        "workflow references unknown pipeline steps: missing_publication" in error
        for error in errors
    )


def test_validate_config_tree_reports_provider_entity_inventory_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    configs_root = _build_minimal_crossref_tree(tmp_path)

    provider_path = configs_root / "providers" / "crossref.yaml"
    provider_payload = _load_yaml(provider_path)
    provider_payload["entities"] = ["publication", "missing_entity"]
    _write_yaml(provider_path, provider_payload)

    errors, warnings, total = module.validate_config_tree(configs_root)

    assert total == 3
    assert not warnings
    assert any(
        "configs/entities/crossref/missing_entity.yaml" in error for error in errors
    )


def test_validate_config_tree_reports_unknown_composite_pipeline_reference(
    tmp_path: Path,
) -> None:
    module = _load_module()
    configs_root = _build_minimal_crossref_tree(tmp_path)

    composite_path = configs_root / "composites" / "publication.yaml"
    _write_yaml(
        composite_path,
        {
            "composite": {
                "name": "composite_publication",
                "version": "1.0.0",
                "seed": {
                    "pipeline": "crossref_publication",
                    "output_keys": ["doi"],
                    "silver_table": "silver/crossref/publication",
                },
                "enrichers": [
                    {
                        "pipeline": "missing_publication",
                        "join_keys": ["doi"],
                    }
                ],
                "merge": {
                    "output": {
                        "silver": "silver/composite/publication",
                        "gold": "gold/composite/publication",
                    },
                    "sort_by": {
                        "silver": ["entity_id", "doi"],
                        "gold": ["entity_id", "doi"],
                    },
                },
            }
        },
    )

    errors, warnings, total = module.validate_config_tree(configs_root)

    assert total == 4
    assert not warnings
    assert any(
        "composite references unknown pipelines: missing_publication" in error
        for error in errors
    )


def test_validate_config_tree_includes_registry_manifest_validation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    configs_root = _build_minimal_crossref_tree(tmp_path)

    errors, warnings, total = module.validate_config_tree(
        configs_root,
        registry_validator=lambda _root: ["registry drift detected"],
    )

    assert total == 3
    assert not warnings
    assert "registry drift detected" in errors


def test_validate_config_tree_reports_legacy_pipeline_dir_reintroduction(
    tmp_path: Path,
) -> None:
    module = _load_module()
    configs_root = _build_minimal_crossref_tree(tmp_path)
    legacy_dir = configs_root / "pipelines"
    legacy_dir.mkdir(parents=True)

    errors, warnings, total = module.validate_config_tree(configs_root)

    assert total == 3
    assert not warnings
    assert any(
        "Legacy pipeline config directory must remain absent" in error
        for error in errors
    )
