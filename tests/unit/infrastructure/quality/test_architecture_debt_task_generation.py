"""Unit tests for architecture debt task generation helpers."""

from __future__ import annotations

import pytest

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

import yaml

from bioetl.infrastructure.quality import architecture_debt_task_generation as tasks
from bioetl.infrastructure.quality.architecture_debt_task_generation import (
    generate_architecture_debt_tasks_payload,
)


pytestmark = pytest.mark.unit


def _write_registry(path: Path, *, registries: dict[str, object]) -> None:
    payload = {
        "schema_version": 1,
        "registries": {
            "file_size_limits": {},
            "function_complexity": {},
            "function_length": {},
            "class_size": {},
            "class_method_count": {},
            "god_object": {},
            "domain_complexity": {},
            **registries,
        },
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_tasks_payload_measures_file_size_entry(tmp_path: Path) -> None:
    module_path = tmp_path / "src" / "bioetl" / "domain" / "sample_module.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(
        "def alpha() -> int:\n    value = 1\n    return value\n",
        encoding="utf-8",
    )
    registry_path = tmp_path / "registry.yaml"
    _write_registry(
        registry_path,
        registries={
            "file_size_limits": {
                "src/bioetl/domain/sample_module.py": {
                    "value": 2,
                    "owner": "@bioetl-architecture",
                    "reason": "trim me",
                    "expires_on": "2026-06-30",
                    "removal_step": "reduce file LOC",
                }
            }
        },
    )

    payload = generate_architecture_debt_tasks_payload(
        registry_path=registry_path,
        project_root=tmp_path,
        generated_at=datetime(2026, 4, 4, 9, 30, tzinfo=UTC),
    )

    assert payload["registry_summary"] == {
        "file_size_limits": 1,
        "function_complexity": 0,
        "function_length": 0,
        "class_size": 0,
        "class_method_count": 0,
        "god_object": 0,
        "domain_complexity": 0,
        "total_tasks": 1,
    }
    task = payload["tasks"][0]
    assert task["target_file"] == "src/bioetl/domain/sample_module.py"
    assert task["current_value"] == 3
    assert task["status"] == "needs_refactor"
    assert task["delta_to_limit"] == 1


def test_generate_tasks_payload_resolves_function_symbol(tmp_path: Path) -> None:
    module_path = tmp_path / "src" / "bioetl" / "application" / "worker.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(
        "def long_worker() -> int:\n"
        "    total = 0\n"
        "    total += 1\n"
        "    total += 2\n"
        "    return total\n",
        encoding="utf-8",
    )
    registry_path = tmp_path / "registry.yaml"
    _write_registry(
        registry_path,
        registries={
            "function_length": {
                "src/bioetl/application/worker.py::long_worker": {
                    "value": 10,
                    "owner": "@bioetl-platform",
                    "reason": "known debt",
                    "expires_on": "2026-06-30",
                    "removal_step": "split helper",
                }
            }
        },
    )

    payload = generate_architecture_debt_tasks_payload(
        registry_path=registry_path,
        project_root=tmp_path,
        generated_at=datetime(2026, 4, 4, 9, 45, tzinfo=UTC),
    )

    task = payload["tasks"][0]
    assert task["target_file"] == "src/bioetl/application/worker.py"
    assert task["symbol_name"] == "long_worker"
    assert task["current_value"] == 5
    assert task["status"] == "within_limit"


def test_generate_tasks_payload_adds_artifact_backlog_tasks(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yaml"
    _write_registry(registry_path, registries={})
    compatibility_path = tmp_path / "compatibility.json"
    duplication_path = tmp_path / "duplication.json"
    hotspot_path = tmp_path / "hotspot.json"
    dead_code_path = tmp_path / "dead-code.json"
    debt_scorecard_path = tmp_path / "debt_scorecard.yaml"

    _write_json(
        compatibility_path,
        {
            "summary": {
                "sanctioned_public_entrypoint_count": 3,
                "sanctioned_public_export_facade_count": 2,
            }
        },
    )
    _write_json(
        duplication_path,
        {
            "targets": [
                {
                    "target": "src/bioetl/interfaces/cli",
                    "duplicate_count": 5,
                    "actionability": [{"category": "command_shell_overlap"}],
                }
            ]
        },
    )
    _write_json(
        hotspot_path,
        {
            "families": [
                {
                    "name": "composition_bootstrap_runtime",
                    "owner": "@bioetl-platform",
                    "path_prefixes": ["src/bioetl/composition/bootstrap/runtime/"],
                    "budget_warnings": ["at_budget:max_internal_fan_in=3/3"],
                }
            ]
        },
    )
    _write_json(
        dead_code_path,
        {
            "summary": {
                "repo_wide_zero_import_candidate_count": 4,
            },
            "review_window": {
                "mode": "fail-fast-zero-untriaged",
            },
        },
    )
    debt_scorecard_path.write_text(
        yaml.safe_dump(
            {
                "sanctioned_public_entrypoint_governance": {
                    "metrics": {
                        "public_entrypoint_count": {
                            "owner": "@bioetl-architecture"
                        }
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = generate_architecture_debt_tasks_payload(
        registry_path=registry_path,
        project_root=tmp_path,
        generated_at=datetime(2026, 4, 4, 10, 0, tzinfo=UTC),
        compatibility_census_path=compatibility_path,
        duplication_baseline_path=duplication_path,
        hotspot_baseline_path=hotspot_path,
        dead_code_inventory_path=dead_code_path,
        debt_scorecard_path=debt_scorecard_path,
    )

    task_ids = {task["id"] for task in payload["tasks"]}
    task_families = {task.get("task_family") for task in payload["tasks"]}
    assert {"ARD-COMPAT-001", "ARD-COMPAT-002", "ARD-DUP-001", "ARD-HOT-001", "ARD-DEAD-001"} <= task_ids
    assert {
        "compatibility_surface",
        "duplication_cluster",
        "hotspot_family",
        "dead_code_review",
    } <= task_families
    assert payload["registry_summary"]["total_tasks"] == 5


def test_default_output_path_uses_quality_reports_directory(tmp_path: Path) -> None:
    generated_at = datetime(2026, 4, 4, 10, 5, tzinfo=UTC)

    output_path = tasks._default_output_path(
        project_root=tmp_path,
        generated_at=generated_at,
    )

    assert output_path == (
        tmp_path
        / "reports"
        / "quality"
        / "tasks_architecture_metric_exemptions_2026-04-04-10-05.json"
    )


def test_project_root_resolves_repository_root() -> None:
    assert (tasks._project_root() / "pyproject.toml").exists()


def test_generate_tasks_payload_requires_explicit_generated_at(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "registry.yaml"
    _write_registry(registry_path, registries={})

    with pytest.raises(ValueError, match="generated_at must be provided"):
        generate_architecture_debt_tasks_payload(
            registry_path=registry_path,
            project_root=tmp_path,
        )


@pytest.mark.parametrize(
    ("registry_name", "goal_fragment", "expected_check_fragment"),
    [
        (
            "function_complexity",
            "cyclomatic complexity",
            "TestFunctionComplexity",
        ),
        (
            "domain_complexity",
            "cyclomatic complexity",
            "TestFunctionComplexity",
        ),
        (
            "class_size",
            "размер класса",
            "test_class_size_registry_has_no_stale_entries",
        ),
        (
            "class_method_count",
            "число методов класса",
            "TestClassSize",
        ),
        (
            "god_object",
            "god object",
            "TestGodObjectDetection",
        ),
    ],
)
def test_generated_tasks_include_registry_specific_goals_and_checks(
    registry_name: str,
    goal_fragment: str,
    expected_check_fragment: str,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "registry.yaml"
    _write_registry(
        registry_path,
        registries={
            registry_name: {
                "MissingSymbol": {
                    "value": 3,
                    "owner": "@bioetl-architecture",
                    "reason": "exercise registry-specific task metadata",
                    "expires_on": "2026-06-30",
                    "removal_step": "reduce metric",
                }
            }
        },
    )

    payload = generate_architecture_debt_tasks_payload(
        registry_path=registry_path,
        project_root=tmp_path,
        generated_at=datetime(2026, 4, 4, 10, 15, tzinfo=UTC),
    )

    task = payload["tasks"][0]
    assert goal_fragment in task["goal"]
    assert any(expected_check_fragment in check for check in task["checks"])
    assert task["status"] == "target_not_found"
