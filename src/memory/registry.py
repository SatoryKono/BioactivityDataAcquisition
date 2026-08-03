"""Loading and semantic validation for the AI memory surface registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memory.resources import discover_memory_root, load_yaml_resource

REGISTRY_RELATIVE_PATH = Path("catalog/memory_registry.yaml")
REQUIRED_SURFACE_FIELDS = frozenset(
    {
        "memory_id",
        "agent_or_runtime",
        "memory_type",
        "subtype",
        "path_or_backend",
        "format",
        "scope",
        "owner",
        "canonicality",
        "source_of_truth",
        "readers",
        "writers",
        "lifetime",
        "retention_policy",
        "cleanup_policy",
        "load_trigger",
        "write_trigger",
        "version_binding",
        "branch_binding",
        "freshness_mechanism",
        "invalidation_mechanism",
        "conflict_resolution",
        "concurrency_model",
        "provenance",
        "security_classification",
        "contains_secrets_or_pii",
        "runtime_usage_proven",
        "evidence",
        "status",
        "risks",
    }
)
CANONICALITIES = frozenset(
    {
        "canonical",
        "derived",
        "mirror",
        "generated",
        "transient",
        "cache",
        "local-only",
        "legacy",
        "unknown",
    }
)
MEMORY_TYPES = frozenset(
    {
        "contextual",
        "working",
        "episodic",
        "semantic",
        "procedural",
        "project",
        "user",
        "shared",
        "tool",
        "cache",
        "evidence",
        "decision",
    }
)
STATUSES = frozenset({"PASS", "WARN", "FAIL", "NOT_PROVEN", "NOT_APPLICABLE"})


@dataclass(frozen=True, slots=True)
class RegistryIssue:
    """One deterministic registry validation failure."""

    path: str
    message: str


def load_memory_registry(root: Path | None = None) -> dict[str, Any]:
    """Load the repository-scoped memory registry."""
    memory_root = (root or discover_memory_root()).resolve()
    payload = load_yaml_resource(memory_root / REGISTRY_RELATIVE_PATH)
    if not isinstance(payload, dict):
        raise ValueError("memory registry root must be a mapping")
    return payload


def _validate_string_list(
    surface: dict[str, Any],
    field: str,
    path: str,
    issues: list[RegistryIssue],
) -> None:
    value = surface.get(field)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        issues.append(
            RegistryIssue(path=path, message=f"{field} must be a non-empty string list")
        )
    elif len(value) != len(set(value)):
        issues.append(RegistryIssue(path=path, message=f"{field} must be unique"))


def validate_memory_registry(payload: Any) -> list[RegistryIssue]:
    """Validate registry completeness and cross-entry ownership invariants."""
    issues: list[RegistryIssue] = []
    if not isinstance(payload, dict):
        return [RegistryIssue("catalog/memory_registry.yaml", "root must be a mapping")]
    if payload.get("schema_version") != 1:
        issues.append(
            RegistryIssue("catalog/memory_registry.yaml", "schema_version must equal 1")
        )
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        issues.append(
            RegistryIssue(
                "catalog/memory_registry.yaml", "surfaces must be a non-empty list"
            )
        )
        return issues

    seen_ids: set[str] = set()
    for index, raw_surface in enumerate(surfaces):
        path = f"catalog/memory_registry.yaml#surfaces[{index}]"
        if not isinstance(raw_surface, dict):
            issues.append(RegistryIssue(path, "surface must be a mapping"))
            continue
        missing = sorted(REQUIRED_SURFACE_FIELDS - raw_surface.keys())
        if missing:
            issues.append(
                RegistryIssue(path, f"missing required fields: {', '.join(missing)}")
            )
        unexpected = sorted(raw_surface.keys() - REQUIRED_SURFACE_FIELDS)
        if unexpected:
            issues.append(
                RegistryIssue(path, f"unexpected fields: {', '.join(unexpected)}")
            )
        memory_id = raw_surface.get("memory_id")
        if not isinstance(memory_id, str) or not memory_id.startswith("MEM-"):
            issues.append(RegistryIssue(path, "memory_id must start with MEM-"))
        elif memory_id in seen_ids:
            issues.append(RegistryIssue(path, f"duplicate memory_id: {memory_id}"))
        else:
            seen_ids.add(memory_id)
        owner = raw_surface.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            issues.append(RegistryIssue(path, "owner must be a non-empty string"))
        canonicality = raw_surface.get("canonicality")
        if canonicality not in CANONICALITIES:
            issues.append(RegistryIssue(path, f"invalid canonicality: {canonicality}"))
        memory_type = raw_surface.get("memory_type")
        if memory_type not in MEMORY_TYPES:
            issues.append(RegistryIssue(path, f"invalid memory_type: {memory_type}"))
        if canonicality == "mirror" and not raw_surface.get("source_of_truth"):
            issues.append(RegistryIssue(path, "mirror must declare source_of_truth"))
        status = raw_surface.get("status")
        if status not in STATUSES:
            issues.append(RegistryIssue(path, f"invalid status: {status}"))
        proven = raw_surface.get("runtime_usage_proven")
        if not isinstance(proven, bool):
            issues.append(RegistryIssue(path, "runtime_usage_proven must be a boolean"))
        if proven is False and status != "NOT_PROVEN":
            issues.append(
                RegistryIssue(
                    path,
                    "unproven runtime usage must have NOT_PROVEN status",
                )
            )
        for field in ("readers", "writers", "evidence", "risks"):
            _validate_string_list(raw_surface, field, path, issues)
    return issues
