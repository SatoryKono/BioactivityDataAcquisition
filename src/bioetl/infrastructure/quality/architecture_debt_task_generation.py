"""Generate architecture-debt task payloads from the exemptions registry."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final, cast

from bioetl.infrastructure.quality.architecture_debt_artifact_tasks import (
    artifact_defaults as _artifact_defaults,
)
from bioetl.infrastructure.quality.architecture_debt_artifact_tasks import (
    build_compatibility_surface_tasks as _build_compatibility_surface_tasks,
)
from bioetl.infrastructure.quality.architecture_debt_artifact_tasks import (
    build_dead_code_review_tasks as _build_dead_code_review_tasks,
)
from bioetl.infrastructure.quality.architecture_debt_artifact_tasks import (
    build_duplication_tasks as _build_duplication_tasks,
)
from bioetl.infrastructure.quality.architecture_debt_artifact_tasks import (
    build_hotspot_family_tasks as _build_hotspot_family_tasks,
)
from bioetl.infrastructure.quality.architecture_debt_task_policy import (
    COMMON_ACCEPTANCE_CRITERIA,
    COMMON_ALLOWED_PATHS,
    COMMON_CHECKS,
    COMMON_FORBIDDEN_PATHS,
)
from bioetl.infrastructure.quality.architecture_debt_task_policy import (
    build_checks as _build_checks,
)
from bioetl.infrastructure.quality.architecture_debt_task_policy import (
    build_goal as _build_goal,
)
from bioetl.infrastructure.quality.architecture_debt_task_support import (
    SymbolMetricLocation,
    build_symbol_index,
    measure_task,
    parse_limit_value,
    task_status,
)
from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry

TASK_SCHEMA_VERSION: Final[str] = "1.0"
REGISTRY_NAMES: Final[tuple[str, ...]] = (
    "file_size_limits",
    "function_complexity",
    "function_length",
    "class_size",
    "class_method_count",
    "god_object",
    "domain_complexity",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_output_path(
    *,
    project_root: Path,
    generated_at: datetime,
) -> Path:
    file_name = (
        "tasks_architecture_metric_exemptions_"
        f"{generated_at.strftime('%Y-%m-%d-%H-%M')}.json"
    )
    return project_root / "reports" / "quality" / file_name


def _require_generated_at(generated_at: datetime | None) -> datetime:
    if generated_at is None:
        raise ValueError("generated_at must be provided by the caller")
    return generated_at


def _resolve_registry_entries(
    *,
    registries: dict[str, object],
    registry_name: str,
) -> dict[str, object]:
    """Return normalized registry entries for one exemption family."""
    entries_raw = registries.get(registry_name, {})
    return cast(dict[str, object], entries_raw if isinstance(entries_raw, dict) else {})


def _build_debt_task(
    *,
    registry_name: str,
    ordinal: int,
    key: str,
    entry: dict[str, object],
    project_root: Path,
    symbol_index: dict[str, list[SymbolMetricLocation]],
) -> dict[str, object]:
    """Build one machine-readable debt task from a registry entry."""
    limit_value = parse_limit_value(entry)
    target_file, symbol_name, current_value, metric_notes = measure_task(
        registry_name=registry_name,
        key=key,
        project_root=project_root,
        symbol_index=symbol_index,
    )
    status = task_status(
        registry_name=registry_name,
        current_value=current_value,
        limit_value=limit_value,
        target_file=target_file,
    )
    delta_to_limit = (
        current_value - limit_value
        if isinstance(current_value, int) and isinstance(limit_value, int)
        else None
    )
    return {
        "id": f"AME-{registry_name.upper()}-{ordinal:03d}",
        "registry": registry_name,
        "registry_key": key,
        "owner": entry.get("owner"),
        "reason": entry.get("reason"),
        "expires_on": entry.get("expires_on"),
        "removal_step": entry.get("removal_step"),
        "limit_value": limit_value,
        "current_value": current_value,
        "delta_to_limit": delta_to_limit,
        "status": status,
        "target_file": target_file,
        "symbol_name": symbol_name,
        "goal": _build_goal(registry_name, limit_value=limit_value),
        "acceptance_criteria": list(COMMON_ACCEPTANCE_CRITERIA),
        "allowed_paths": list(COMMON_ALLOWED_PATHS),
        "forbidden_paths": list(COMMON_FORBIDDEN_PATHS),
        "checks": _build_checks(registry_name),
        "notes": metric_notes,
    }


def generate_architecture_debt_tasks_payload(
    *,
    registry_path: Path | str | None = None,
    project_root: Path | str | None = None,
    generated_at: datetime | None = None,
    compatibility_census_path: Path | str | None = None,
    duplication_baseline_path: Path | str | None = None,
    hotspot_baseline_path: Path | str | None = None,
    dead_code_inventory_path: Path | str | None = None,
    debt_scorecard_path: Path | str | None = None,
) -> dict[str, object]:
    """Build a refactoring task payload from the exemptions registry."""
    resolved_project_root = (
        Path(project_root) if project_root is not None else _project_root()
    )
    registry = load_exemptions_registry(registry_path)
    registries_raw = registry.get("registries", {})
    registries = cast(
        dict[str, object],
        registries_raw if isinstance(registries_raw, dict) else {},
    )
    timestamp = _require_generated_at(generated_at)
    symbol_index = build_symbol_index(resolved_project_root)
    artifact_paths = _artifact_defaults(resolved_project_root)
    if compatibility_census_path is not None:
        artifact_paths["compatibility_census"] = Path(compatibility_census_path)
    if duplication_baseline_path is not None:
        artifact_paths["duplication_baseline"] = Path(duplication_baseline_path)
    if hotspot_baseline_path is not None:
        artifact_paths["hotspot_baseline"] = Path(hotspot_baseline_path)
    if dead_code_inventory_path is not None:
        artifact_paths["dead_code_inventory"] = Path(dead_code_inventory_path)
    if debt_scorecard_path is not None:
        artifact_paths["debt_scorecard"] = Path(debt_scorecard_path)

    tasks: list[dict[str, object]] = []
    registry_summary: dict[str, int] = {}

    for registry_name in REGISTRY_NAMES:
        entries = _resolve_registry_entries(
            registries=registries,
            registry_name=registry_name,
        )
        registry_summary[registry_name] = len(entries)

        for ordinal, (key, entry_raw) in enumerate(sorted(entries.items()), start=1):
            entry = cast(
                dict[str, object],
                entry_raw if isinstance(entry_raw, dict) else {},
            )
            tasks.append(
                _build_debt_task(
                    registry_name=registry_name,
                    ordinal=ordinal,
                    key=key,
                    entry=entry,
                    project_root=resolved_project_root,
                    symbol_index=symbol_index,
                )
            )

    artifact_tasks = [
        *_build_compatibility_surface_tasks(
            artifact_paths=artifact_paths,
        ),
        *_build_duplication_tasks(artifact_paths=artifact_paths),
        *_build_hotspot_family_tasks(artifact_paths=artifact_paths),
        *_build_dead_code_review_tasks(artifact_paths=artifact_paths),
    ]
    tasks.extend(artifact_tasks)

    registry_summary["total_tasks"] = len(tasks)
    return {
        "schema_version": TASK_SCHEMA_VERSION,
        "source_registry_file": (
            Path(registry_path).as_posix()
            if registry_path is not None
            else "configs/quality/architecture_metric_exemptions.yaml"
        ),
        "generated_at": timestamp.isoformat(),
        "defaults": {
            "behavior_change_allowed": False,
            "public_interface_change_allowed": False,
            "docstrings_rule": (
                "Докстринги: не удалять. Разрешено только изменять с соблюдением "
                "стандартов докстрингов проекта."
            ),
        },
        "registry_summary": registry_summary,
        "tasks": tasks,
    }


__all__ = [
    "COMMON_ACCEPTANCE_CRITERIA",
    "COMMON_ALLOWED_PATHS",
    "COMMON_CHECKS",
    "COMMON_FORBIDDEN_PATHS",
    "REGISTRY_NAMES",
    "TASK_SCHEMA_VERSION",
    "SymbolMetricLocation",
    "_default_output_path",
    "generate_architecture_debt_tasks_payload",
]
