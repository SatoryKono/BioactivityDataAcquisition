"""Generate architecture-debt task payloads from the exemptions registry."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final, cast

from bioetl.infrastructure.quality.architecture_debt_artifact_tasks import (
    artifact_defaults as _artifact_defaults,
    build_compatibility_surface_tasks as _build_compatibility_surface_tasks,
    build_dead_code_review_tasks as _build_dead_code_review_tasks,
    build_duplication_tasks as _build_duplication_tasks,
    build_hotspot_family_tasks as _build_hotspot_family_tasks,
)
from bioetl.infrastructure.quality.architecture_debt_task_policy import (
    COMMON_ACCEPTANCE_CRITERIA,
    COMMON_ALLOWED_PATHS,
    COMMON_CHECKS,
    COMMON_FORBIDDEN_PATHS,
    build_checks as _build_checks,
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
COMMON_ACCEPTANCE_CRITERIA: Final[tuple[str, ...]] = (
    "Поведение не изменено",
    "Публичные интерфейсы не изменены",
    "Докстринги не удалены; изменения соответствуют стандартам проекта",
)
COMMON_ALLOWED_PATHS: Final[tuple[str, ...]] = ("src/bioetl/**", "tests/**")


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


def _build_checks(registry_name: str) -> list[str]:
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


def _artifact_checks(task_family: str) -> list[str]:
    return [*ARTIFACT_CHECKS[task_family], *COMMON_CHECKS]


def _build_goal(registry_name: str, *, limit_value: object) -> str:
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


def _load_json_if_present(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, object], payload if isinstance(payload, dict) else {})


def _load_yaml_if_present(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return cast(dict[str, object], payload if isinstance(payload, dict) else {})


def _artifact_defaults(project_root: Path) -> dict[str, Path]:
    quality_root = project_root / "reports" / "quality"
    return {
        "compatibility_census": quality_root / "compatibility-importer-census.json",
        "duplication_baseline": quality_root / "full-app-duplication-baseline.json",
        "hotspot_baseline": quality_root / "hotspot-family-baseline.json",
        "dead_code_inventory": quality_root / "dead-code-inventory.json",
        "debt_scorecard": project_root / "configs" / "quality" / "debt_scorecard.yaml",
    }


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


def _build_artifact_task(
    *,
    task_id: str,
    task_family: str,
    registry_key: str,
    owner: object,
    current_value: int,
    limit_value: int | None,
    target_file: str | None,
    source_artifact: str,
    goal: str,
    notes: list[str],
) -> dict[str, object]:
    delta_to_limit = (
        current_value - limit_value
        if isinstance(limit_value, int)
        else current_value
    )
    return {
        "id": task_id,
        "task_family": task_family,
        "registry": "artifact_governance",
        "registry_key": registry_key,
        "owner": owner,
        "reason": f"Generated from {source_artifact}",
        "expires_on": None,
        "removal_step": "refresh_artifact_and_reduce_live_count",
        "limit_value": limit_value,
        "current_value": current_value,
        "delta_to_limit": delta_to_limit,
        "status": "needs_refactor",
        "target_file": target_file,
        "symbol_name": None,
        "goal": goal,
        "acceptance_criteria": list(COMMON_ACCEPTANCE_CRITERIA),
        "allowed_paths": list(COMMON_ALLOWED_PATHS),
        "forbidden_paths": list(COMMON_FORBIDDEN_PATHS),
        "checks": _artifact_checks(task_family),
        "notes": notes,
        "source_artifact": source_artifact,
    }


def _build_compatibility_surface_tasks(
    *,
    project_root: Path,
    artifact_paths: dict[str, Path],
) -> list[dict[str, object]]:
    census = _load_json_if_present(artifact_paths["compatibility_census"])
    if not census:
        return []
    summary = cast(dict[str, object], census.get("summary", {}))
    scorecard = _load_yaml_if_present(artifact_paths["debt_scorecard"])
    governance = cast(
        dict[str, object],
        scorecard.get("sanctioned_public_entrypoint_governance", {}),
    )
    metrics = cast(dict[str, object], governance.get("metrics", {}))
    tasks: list[dict[str, object]] = []

    public_entrypoint_count = int(
        summary.get(
            "sanctioned_public_entrypoint_count",
            summary.get("retained_entrypoint_count", 0),
        )
    )
    if public_entrypoint_count > 0:
        tasks.append(
            _build_artifact_task(
                task_id="ARD-COMPAT-001",
                task_family="compatibility_surface",
                registry_key="sanctioned_public_entrypoint_governance.public_entrypoint_count",
                owner=cast(
                    dict[str, object],
                    metrics.get("public_entrypoint_count", {}),
                ).get("owner", "@bioetl-architecture"),
                current_value=public_entrypoint_count,
                limit_value=0,
                target_file=None,
                source_artifact="reports/quality/compatibility-importer-census.json",
                goal=(
                    "Свести публичную compatibility/governance burden к "
                    "минимально необходимому набору санкционированных entrypoint seams."
                ),
                notes=[
                    f"sanctioned_public_entrypoint_count={public_entrypoint_count}",
                    "Review sanctioned public API inventory before adding or retaining seams.",
                ],
            )
        )

    public_export_count = int(
        summary.get(
            "sanctioned_public_export_facade_count",
            summary.get("retained_public_export_facade_count", 0),
        )
    )
    if public_export_count > 0:
        tasks.append(
            _build_artifact_task(
                task_id="ARD-COMPAT-002",
                task_family="compatibility_surface",
                registry_key="sanctioned_public_entrypoint_governance.public_export_facade_count",
                owner="@bioetl-architecture",
                current_value=public_export_count,
                limit_value=0,
                target_file=None,
                source_artifact="reports/quality/compatibility-importer-census.json",
                goal=(
                    "Сократить число публичных lazy/export facade seams или "
                    "жёстко удерживать их без роста как отдельный governance surface."
                ),
                notes=[
                    f"sanctioned_public_export_facade_count={public_export_count}",
                    "Collapse reviewed facade burden before introducing new package-root exports.",
                ],
            )
        )
    return tasks


def _build_duplication_tasks(
    *,
    artifact_paths: dict[str, Path],
) -> list[dict[str, object]]:
    baseline = _load_json_if_present(artifact_paths["duplication_baseline"])
    targets = baseline.get("targets", [])
    if not isinstance(targets, list):
        return []
    tasks: list[dict[str, object]] = []
    for ordinal, row in enumerate(targets, start=1):
        if not isinstance(row, dict):
            continue
        duplicate_count = int(row.get("duplicate_count", 0))
        if duplicate_count <= 0:
            continue
        target = str(row.get("target", ""))
        actionability = row.get("actionability", [])
        categories: list[str] = []
        if isinstance(actionability, list):
            categories = [
                str(item.get("category"))
                for item in actionability
                if isinstance(item, dict) and item.get("category")
            ]
        tasks.append(
            _build_artifact_task(
                task_id=f"ARD-DUP-{ordinal:03d}",
                task_family="duplication_cluster",
                registry_key=target,
                owner="@bioetl-architecture",
                current_value=duplicate_count,
                limit_value=0,
                target_file=target,
                source_artifact="reports/quality/full-app-duplication-baseline.json",
                goal=(
                    f"Снизить duplicate clusters в `{target}` до нуля или "
                    "ниже следующего ratchet review."
                ),
                notes=[
                    f"duplicate_count={duplicate_count}",
                    (
                        "actionability_categories="
                        + (", ".join(categories) if categories else "none")
                    ),
                ],
            )
        )
    return tasks


def _build_hotspot_family_tasks(
    *,
    artifact_paths: dict[str, Path],
) -> list[dict[str, object]]:
    baseline = _load_json_if_present(artifact_paths["hotspot_baseline"])
    families = baseline.get("families", [])
    if not isinstance(families, list):
        return []
    tasks: list[dict[str, object]] = []
    for ordinal, row in enumerate(families, start=1):
        if not isinstance(row, dict):
            continue
        warnings = row.get("budget_warnings", [])
        if not isinstance(warnings, list) or not warnings:
            continue
        path_prefixes = row.get("path_prefixes", [])
        target_file = (
            str(path_prefixes[0]) if isinstance(path_prefixes, list) and path_prefixes else None
        )
        tasks.append(
            _build_artifact_task(
                task_id=f"ARD-HOT-{ordinal:03d}",
                task_family="hotspot_family",
                registry_key=str(row.get("name", f"family-{ordinal}")),
                owner=row.get("owner", "@bioetl-architecture"),
                current_value=len(warnings),
                limit_value=0,
                target_file=target_file,
                source_artifact="reports/quality/hotspot-family-baseline.json",
                goal=(
                    "Снять hotspot family budget warnings через декомпозицию "
                    "size/fan-in pressure без роста debt budget."
                ),
                notes=[str(warning) for warning in warnings],
            )
        )
    return tasks


def _build_dead_code_review_tasks(
    *,
    artifact_paths: dict[str, Path],
) -> list[dict[str, object]]:
    inventory = _load_json_if_present(artifact_paths["dead_code_inventory"])
    if not inventory:
        return []
    summary = cast(dict[str, object], inventory.get("summary", {}))
    retained_candidates = int(summary.get("repo_wide_zero_import_candidate_count", 0))
    if retained_candidates <= 0:
        return []
    review_window = cast(dict[str, object], inventory.get("review_window", {}))
    return [
        _build_artifact_task(
            task_id="ARD-DEAD-001",
            task_family="dead_code_review",
            registry_key="repo_wide_zero_import_candidate_count",
            owner="@bioetl-architecture",
            current_value=retained_candidates,
            limit_value=0,
            target_file=None,
            source_artifact="reports/quality/dead-code-inventory.json",
            goal=(
                "Продолжить review/removal wave по zero-import candidate surfaces "
                "без роста untriaged residual."
            ),
            notes=[
                f"repo_wide_zero_import_candidate_count={retained_candidates}",
                f"review_mode={review_window.get('mode', 'unknown')}",
            ],
        )
    ]


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
            project_root=resolved_project_root,
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
