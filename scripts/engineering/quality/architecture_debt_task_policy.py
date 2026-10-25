"""Shared policy constants and helpers for architecture debt task generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, cast

import yaml

COMMON_ACCEPTANCE_CRITERIA: Final[tuple[str, ...]] = (
    "Поведение не изменено",
    "Публичные интерфейсы не изменены",
    "Докстринги не удалены; изменения соответствуют стандартам проекта",
)
COMMON_ALLOWED_PATHS: Final[tuple[str, ...]] = ("src/bioetl/**", "tests/**")
COMMON_FORBIDDEN_PATHS: Final[tuple[str, ...]] = (
    "configs/**",
    "docs/**",
    ".github/**",
)
COMMON_CHECKS: Final[tuple[str, ...]] = (
    "python -m pytest -q "
    "tests/architecture/test_quality_debt_scorecard.py "
    "tests/architecture/test_quality_exemptions_registry.py",
    "python -m scripts.engineering.qa check-exemptions --mode auto --growth-mode auto --trend-report off",
)
ARTIFACT_CHECKS: Final[dict[str, tuple[str, ...]]] = {
    "compatibility_surface": (
        "python -m pytest -q tests/architecture/test_public_facade_inventory.py",
        "python -m pytest -q tests/architecture/test_public_surface_importer_census_governance.py",
    ),
    "duplication_cluster": (
        "python -m pytest -q tests/architecture/test_tech_debt_issues_5626_5637_closeout.py",
        "python -m scripts.engineering.qa report-duplication-baseline --help",
    ),
    "hotspot_family": (
        "python -m pytest -q tests/architecture/test_quality_debt_scorecard.py",
        "python -m scripts.engineering.qa report-family-baseline --help",
    ),
    "dead_code_review": (
        "python -m pytest -q tests/architecture/test_tech_debt_issues_5626_5637_closeout.py",
        "python -m scripts.engineering.qa report-dead-code-inventory --help",
    ),
}


def build_checks(registry_name: str) -> list[str]:
    per_registry = {
        "file_size_limits": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestFileSizeLimits",
            "python -m pytest -q "
            "tests/architecture/test_quality_burndown_priorities.py::"
            "test_file_size_limit_registry_has_no_stale_entries",
        ],
        "function_length": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionLength",
            "python -m pytest -q "
            "tests/architecture/test_quality_burndown_priorities.py::"
            "test_function_length_registry_has_no_stale_entries",
        ],
        "function_complexity": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionComplexity",
        ],
        "domain_complexity": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionComplexity",
        ],
        "class_size": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize",
            "python -m pytest -q "
            "tests/architecture/test_quality_burndown_priorities.py::"
            "test_class_size_registry_has_no_stale_entries",
        ],
        "class_method_count": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize",
        ],
        "god_object": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestGodObjectDetection",
        ],
    }
    return [*per_registry[registry_name], *COMMON_CHECKS]


def artifact_checks(task_family: str) -> list[str]:
    return [*ARTIFACT_CHECKS[task_family], *COMMON_CHECKS]


def build_goal(registry_name: str, *, limit_value: object) -> str:
    if registry_name == "file_size_limits":
        return f"Снизить LOC файла до {limit_value} или ниже без изменения поведения."
    if registry_name == "function_length":
        return f"Сократить длину функции до {limit_value} строк или ниже."
    if registry_name in {"function_complexity", "domain_complexity"}:
        return (
            f"Снизить cyclomatic complexity до {limit_value} или ниже через "
            "extract method, ранние выходы и упрощение branching."
        )
    if registry_name == "class_size":
        return (
            f"Снизить размер класса до {limit_value} LOC или ниже через "
            "декомпозицию ответственности."
        )
    if registry_name == "class_method_count":
        return (
            f"Снизить число методов класса до {limit_value} или ниже через "
            "extraction/move method."
        )
    return (
        "Уменьшить признаки god object через выделение collaborators и "
        "delegation patterns без изменения публичного интерфейса."
    )


def load_json_if_present(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, object], payload if isinstance(payload, dict) else {})


def load_yaml_if_present(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return cast(dict[str, object], payload if isinstance(payload, dict) else {})


__all__ = [
    "ARTIFACT_CHECKS",
    "COMMON_ACCEPTANCE_CRITERIA",
    "COMMON_ALLOWED_PATHS",
    "COMMON_CHECKS",
    "COMMON_FORBIDDEN_PATHS",
    "artifact_checks",
    "build_checks",
    "build_goal",
    "load_json_if_present",
    "load_yaml_if_present",
]
