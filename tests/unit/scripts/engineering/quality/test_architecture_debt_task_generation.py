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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for architecture debt task generation helpers."""

from __future__ import annotations

import pytest

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

import yaml

from bioetl.infrastructure.quality import architecture_debt_task_generation as tasks
from bioetl.infrastructure.quality import architecture_debt_artifact_tasks
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
                "retained_public_export_facades_with_duplicate_exports": 1,
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
                "repo_wide_untriaged_zero_import_candidate_count": 2,
            },
            "review_window": {
                "mode": "fail-fast-zero-untriaged",
            },
        },
    )
    debt_scorecard_path.write_text(
        yaml.safe_dump(
            {
                "compatibility_debt_metrics": {
                    "metrics": {
                        "transition_compat_count": {
                            "current_count": 1,
                            "target_count": 0,
                        },
                        "sunset_compat_count": {
                            "current_count": 0,
                            "target_count": 0,
                        },
                        "expired_compat_count": {
                            "current_count": 0,
                            "max_count": 0,
                        },
                    }
                },
                "sanctioned_public_entrypoint_governance": {
                    "metrics": {
                        "public_entrypoint_count": {
                            "current_count": 3,
                            "owner": "@bioetl-architecture",
                        },
                        "public_export_facade_count": {"current_count": 2},
                        "public_export_facade_conflict_count": {"current_count": 0},
                    }
                },
                "retirement_governance_metrics": {
                    "metrics": {
                        "repo_wide_untriaged_zero_import_candidate_count": {
                            "max_count": 0
                        }
                    }
                },
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
    assert {
        "ARD-COMPAT-001",
        "ARD-COMPAT-006",
        "ARD-DUP-001",
        "ARD-HOT-001",
        "ARD-DEAD-001",
    } <= task_ids
    assert {
        "compatibility_surface",
        "duplication_cluster",
        "hotspot_family",
        "dead_code_review",
    } <= task_families
    assert payload["registry_summary"]["total_tasks"] == 5
    tasks_by_id = {task["id"]: task for task in payload["tasks"]}
    assert tasks_by_id["ARD-COMPAT-001"]["registry_key"] == (
        "compatibility_debt_metrics.transition_compat_count"
    )
    assert tasks_by_id["ARD-COMPAT-006"]["source_artifact"] == (
        "reports/quality/compatibility-importer-census.json"
    )
    assert tasks_by_id["ARD-DEAD-001"]["registry_key"] == (
        "repo_wide_untriaged_zero_import_candidate_count"
    )
    assert {"ARD-COMPAT-004", "ARD-COMPAT-005"}.isdisjoint(task_ids)


def test_generate_tasks_payload_excludes_reviewed_retained_surfaces(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "registry.yaml"
    _write_registry(registry_path, registries={})
    compatibility_path = tmp_path / "compatibility.json"
    dead_code_path = tmp_path / "dead-code.json"
    debt_scorecard_path = tmp_path / "debt_scorecard.yaml"
    _write_json(
        compatibility_path,
        {
            "summary": {
                "retained_entrypoint_count": 12,
                "retained_public_export_facade_count": 4,
                "retained_public_export_facades_with_duplicate_exports": 0,
                "retained_public_export_facades_with_resolution_conflicts": 0,
                "retained_public_export_facades_with_wrapper_contract_drift": 0,
            }
        },
    )
    _write_json(
        dead_code_path,
        {
            "summary": {
                "repo_wide_zero_import_candidate_count": 9,
                "repo_wide_classified_zero_import_candidate_count": 9,
                "repo_wide_untriaged_zero_import_candidate_count": 0,
            }
        },
    )
    debt_scorecard_path.write_text(
        yaml.safe_dump(
            {
                "compatibility_debt_metrics": {
                    "metrics": {
                        "transition_compat_count": {
                            "current_count": 0,
                            "target_count": 0,
                        },
                        "sunset_compat_count": {
                            "current_count": 0,
                            "target_count": 0,
                        },
                        "expired_compat_count": {
                            "current_count": 0,
                            "max_count": 0,
                        },
                    }
                },
                "sanctioned_public_entrypoint_governance": {
                    "metrics": {
                        "public_entrypoint_count": {"current_count": 12},
                        "public_export_facade_count": {"current_count": 4},
                        "public_export_facade_conflict_count": {"current_count": 0},
                    }
                },
                "retirement_governance_metrics": {
                    "metrics": {
                        "repo_wide_untriaged_zero_import_candidate_count": {
                            "max_count": 0
                        }
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = generate_architecture_debt_tasks_payload(
        registry_path=registry_path,
        project_root=tmp_path,
        generated_at=datetime(2026, 7, 19, 10, 0, tzinfo=UTC),
        compatibility_census_path=compatibility_path,
        dead_code_inventory_path=dead_code_path,
        debt_scorecard_path=debt_scorecard_path,
    )

    assert payload["tasks"] == []


def test_generate_tasks_payload_does_not_infer_zero_growth_limit(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "registry.yaml"
    _write_registry(registry_path, registries={})
    compatibility_path = tmp_path / "compatibility.json"
    debt_scorecard_path = tmp_path / "debt_scorecard.yaml"
    _write_json(
        compatibility_path,
        {
            "summary": {
                "retained_entrypoint_count": 12,
                "retained_public_export_facade_count": 4,
            }
        },
    )
    debt_scorecard_path.write_text("{}\n", encoding="utf-8")

    payload = generate_architecture_debt_tasks_payload(
        registry_path=registry_path,
        project_root=tmp_path,
        generated_at=datetime(2026, 7, 19, 10, 5, tzinfo=UTC),
        compatibility_census_path=compatibility_path,
        debt_scorecard_path=debt_scorecard_path,
    )

    assert payload["tasks"] == []


def test_transition_task_counts_do_not_double_count_sunset_or_expired_subsets() -> None:
    generated: list[dict[str, object]] = []
    architecture_debt_artifact_tasks._append_transition_compatibility_tasks(
        generated,
        {
            "transition_compat_count": {"current_count": 1, "target_count": 0},
            "sunset_compat_count": {"current_count": 1, "target_count": 0},
            "expired_compat_count": {"current_count": 1, "max_count": 0},
        },
    )

    assert [task["id"] for task in generated] == ["ARD-COMPAT-003"]
    assert generated[0]["current_value"] == 1


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
