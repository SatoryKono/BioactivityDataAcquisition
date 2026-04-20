"""Validation helpers for the project-memory scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memory.resources import (
    MEMORY_ROOT,
    iter_catalog_paths,
    iter_policy_paths,
    iter_schema_paths,
    load_json_resource,
    load_yaml_resource,
)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Represents a memory-scaffold validation failure."""

    path: str
    message: str


def _validate_exists(path: Path, issues: list[ValidationIssue]) -> None:
    if not path.exists():
        issues.append(ValidationIssue(path=str(path), message="missing required file"))


def _validate_schema_shape(path: Path, payload: Any, issues: list[ValidationIssue]) -> None:
    if not isinstance(payload, dict):
        issues.append(
            ValidationIssue(path=str(path), message="schema root must be a JSON object")
        )
        return
    for key in ("$schema", "title", "type"):
        if key not in payload:
            issues.append(
                ValidationIssue(path=str(path), message=f"schema missing required key: {key}")
            )


def _validate_source_priority(
    policy_payload: dict[str, Any],
    source_registry: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    known_source_ids = {
        item.get("id")
        for item in source_registry.get("sources", [])
        if isinstance(item, dict) and item.get("id")
    }
    ordered_sources = policy_payload.get("ordered_sources", [])
    if not isinstance(ordered_sources, list):
        issues.append(
            ValidationIssue(
                path="policy/source_priority.yaml",
                message="ordered_sources must be a list",
            )
        )
        return
    for source_id in ordered_sources:
        if source_id not in known_source_ids:
            issues.append(
                ValidationIssue(
                    path="policy/source_priority.yaml",
                    message=f"unknown source id in ordered_sources: {source_id}",
                )
            )


def validate_memory_scaffold(root: Path | None = None) -> list[ValidationIssue]:
    """Validate the baseline project-memory scaffold."""
    _ = root or MEMORY_ROOT
    issues: list[ValidationIssue] = []

    for path in (*iter_policy_paths(), *iter_catalog_paths(), *iter_schema_paths()):
        _validate_exists(path, issues)

    if issues:
        return issues

    policy_payloads = {
        path.name: load_yaml_resource(path)
        for path in iter_policy_paths()
    }
    catalog_payloads = {
        path.name: load_yaml_resource(path)
        for path in iter_catalog_paths()
    }
    schema_payloads = {
        path.name: load_json_resource(path)
        for path in iter_schema_paths()
    }

    for name, payload in {**policy_payloads, **catalog_payloads}.items():
        if not isinstance(payload, dict):
            issues.append(
                ValidationIssue(path=name, message="YAML root must be a mapping")
            )

    for name, payload in schema_payloads.items():
        _validate_schema_shape(Path("schemas") / name, payload, issues)

    source_priority = policy_payloads.get("source_priority.yaml")
    source_registry = catalog_payloads.get("source_registry.yaml")
    if isinstance(source_priority, dict) and isinstance(source_registry, dict):
        _validate_source_priority(source_priority, source_registry, issues)

    return issues
