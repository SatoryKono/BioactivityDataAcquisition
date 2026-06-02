"""Unit tests for architecture debt task generation helpers."""

from __future__ import annotations

import pytest

from datetime import UTC
from datetime import datetime
from pathlib import Path

import yaml

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
