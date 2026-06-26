"""Build orchestration plans for architecture-debt reduction work."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Final, cast

PLAN_SCHEMA_VERSION: Final[str] = "1.0"
_CATEGORY_PRIORITY: Final[dict[str, int]] = {
    "COMPATIBILITY_DEBT": 1,
    "DUPLICATION": 2,
    "HOTSPOT_SIZE_COUPLING_DEBT": 3,
    "DEAD_CODE_REVIEW_DEBT": 4,
    "STALE_EXEMPTION": 5,
    "GOD_OBJECT": 6,
    "COMPLEXITY": 7,
    "NEAR_LIMIT": 8,
    "REDUCE_TO_LIMIT": 9,
    "SAFE_MARGIN": 10,
    "TARGET_NOT_FOUND": 11,
}
_FILE_LAYER_LIMITS: Final[dict[str, int]] = {
    "domain": 305,
    "application": 500,
    "composition": 350,
    "infrastructure": 650,
    "interfaces": 420,
}
_COMPLEXITY_LIMITS: Final[dict[str, int]] = {
    "domain": 5,
    "application": 10,
    "infrastructure": 15,
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_plan_output_path(
    *,
    project_root: Path,
    generated_at: datetime,
) -> Path:
    file_name = (
        "architecture_debt_execution_plan_"
        f"{generated_at.strftime('%Y-%m-%d-%H-%M')}.json"
    )
    return project_root / "reports" / "quality" / file_name


def find_latest_architecture_debt_tasks_file(
    *,
    project_root: Path | str | None = None,
) -> Path | None:
    """Return the latest generated architecture debt task file."""
    root = Path(project_root) if project_root is not None else _project_root()
    reports_candidates = sorted(
        (root / "reports" / "quality").glob(
            "tasks_architecture_metric_exemptions_*.json"
        )
    )
    if reports_candidates:
        return reports_candidates[-1]

    legacy_root_candidates = sorted(
        root.glob("tasks_architecture_metric_exemptions_*.json")
    )
    if legacy_root_candidates:
        return legacy_root_candidates[-1]
    return None


def load_architecture_debt_tasks(path: Path | str) -> dict[str, object]:
    """Load a generated architecture debt tasks JSON payload."""
    candidate = Path(path)
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            f"Architecture debt tasks payload must be a mapping: {candidate}"
        )
    return cast(dict[str, object], payload)


def _layer_for_target(target_file: str | None) -> str | None:
    if not target_file:
        return None
    parts = Path(target_file).parts
    if len(parts) < 3 or parts[:2] != ("src", "bioetl"):
        return None
    return parts[2]


def _default_limit(task: dict[str, object]) -> int | None:
    registry = task.get("registry")
    target_file = cast(str | None, task.get("target_file"))
    if registry == "file_size_limits":
        layer = _layer_for_target(target_file)
        return _FILE_LAYER_LIMITS.get(layer or "")
    if registry == "function_length":
        return 100
    if registry == "class_size":
        return 300
    if registry == "class_method_count":
        return 20
    if registry in {"function_complexity", "domain_complexity"}:
        layer = _layer_for_target(target_file)
        return _COMPLEXITY_LIMITS.get(layer or "")
    return None


def _classify_task(task: dict[str, object]) -> str:
    task_family = cast(str | None, task.get("task_family")) or ""
    status = cast(str | None, task.get("status")) or ""
    registry = cast(str | None, task.get("registry")) or ""
    current_value = task.get("current_value")
    delta_to_limit = task.get("delta_to_limit")
    default_limit = _default_limit(task)

    if task_family == "compatibility_surface":
        return "COMPATIBILITY_DEBT"
    if task_family == "duplication_cluster":
        return "DUPLICATION"
    if task_family == "hotspot_family":
        return "HOTSPOT_SIZE_COUPLING_DEBT"
    if task_family == "dead_code_review":
        return "DEAD_CODE_REVIEW_DEBT"
    if status == "target_not_found":
        return "TARGET_NOT_FOUND"
    if registry == "god_object":
        return "GOD_OBJECT"
    if (
        status == "within_limit"
        and isinstance(current_value, int)
        and default_limit is not None
        and current_value <= default_limit
    ):
        return "STALE_EXEMPTION"
    if status == "within_limit" and isinstance(delta_to_limit, int):
        if -5 <= delta_to_limit <= 0:
            return "NEAR_LIMIT"
        if delta_to_limit < -15:
            return "SAFE_MARGIN"
    if registry in {"function_complexity", "domain_complexity"}:
        return "COMPLEXITY"
    return "REDUCE_TO_LIMIT"


def _primary_executor(category: str) -> str:
    if category == "COMPATIBILITY_DEBT":
        return "py-config-bot"
    if category in {"DUPLICATION", "HOTSPOT_SIZE_COUPLING_DEBT"}:
        return "orchestrator"
    if category == "DEAD_CODE_REVIEW_DEBT":
        return "py-audit-bot"
    if category == "STALE_EXEMPTION":
        return "py-config-bot"
    if category == "TARGET_NOT_FOUND":
        return "py-audit-bot"
    return "orchestrator"


def _supporting_agents(category: str) -> list[str]:
    if category == "COMPATIBILITY_DEBT":
        return ["py-test-bot", "py-doc-bot", "py-audit-bot", "py-review-orchestrator"]
    if category in {"DUPLICATION", "HOTSPOT_SIZE_COUPLING_DEBT"}:
        return ["py-test-bot", "py-doc-bot", "py-config-bot", "py-audit-bot"]
    if category == "DEAD_CODE_REVIEW_DEBT":
        return ["py-test-bot", "py-doc-bot", "py-plan-bot"]
    if category == "SAFE_MARGIN":
        return ["py-audit-bot"]
    if category == "TARGET_NOT_FOUND":
        return ["py-plan-bot"]
    agents = ["py-test-bot", "py-doc-bot"]
    if category == "STALE_EXEMPTION":
        agents.append("py-audit-bot")
        return agents
    agents.extend(["py-config-bot", "py-audit-bot", "py-review-orchestrator"])
    return agents


def _requires_config_update(category: str) -> bool:
    return category in {
        "COMPATIBILITY_DEBT",
        "STALE_EXEMPTION",
        "NEAR_LIMIT",
        "REDUCE_TO_LIMIT",
        "COMPLEXITY",
        "GOD_OBJECT",
    }


def _enrich_task(task: dict[str, object], category: str) -> dict[str, object]:
    enriched = dict(task)
    enriched["category"] = category
    enriched["priority"] = _CATEGORY_PRIORITY[category]
    enriched["primary_executor"] = _primary_executor(category)
    enriched["supporting_agents"] = _supporting_agents(category)
    enriched["requires_config_update"] = _requires_config_update(category)
    return enriched


def _build_batch(
    *,
    category: str,
    tasks: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "category": category,
        "priority": _CATEGORY_PRIORITY[category],
        "task_ids": [cast(str, item["id"]) for item in tasks],
        "targets": sorted(
            {
                cast(str, item["target_file"])
                for item in tasks
                if isinstance(item.get("target_file"), str)
            }
        ),
        "primary_executor": _primary_executor(category),
        "supporting_agents": _supporting_agents(category),
    }


def _require_generated_at(generated_at: datetime | None) -> datetime:
    if generated_at is None:
        raise ValueError("generated_at must be provided by the caller")
    return generated_at


def build_architecture_debt_execution_plan(
    tasks_payload: dict[str, object],
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Classify generated tasks into an orchestration plan."""
    timestamp = _require_generated_at(generated_at)
    tasks = cast(list[dict[str, object]], tasks_payload.get("tasks", []))
    categorized: list[dict[str, object]] = []
    category_counts: dict[str, int] = dict.fromkeys(_CATEGORY_PRIORITY, 0)

    for task in tasks:
        category = _classify_task(task)
        category_counts[category] += 1
        categorized.append(_enrich_task(task, category))

    categorized.sort(
        key=lambda item: (
            cast(int, item["priority"]),
            cast(str, item.get("target_file") or ""),
            cast(str, item.get("id") or ""),
        )
    )

    batches: list[dict[str, object]] = []
    current_category = ""
    current_tasks: list[dict[str, object]] = []
    for task in categorized:
        category = cast(str, task["category"])
        if category != current_category and current_tasks:
            batches.append(_build_batch(category=current_category, tasks=current_tasks))
            current_tasks = []
        current_category = category
        current_tasks.append(task)
    if current_tasks:
        batches.append(_build_batch(category=current_category, tasks=current_tasks))

    actionable_categories = {
        "COMPATIBILITY_DEBT",
        "DUPLICATION",
        "HOTSPOT_SIZE_COUPLING_DEBT",
        "DEAD_CODE_REVIEW_DEBT",
        "STALE_EXEMPTION",
        "GOD_OBJECT",
        "COMPLEXITY",
        "NEAR_LIMIT",
        "REDUCE_TO_LIMIT",
    }
    actionable_tasks = sum(category_counts[name] for name in actionable_categories)
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "generated_at": timestamp.isoformat(),
        "source_tasks_file": tasks_payload.get("source_tasks_file"),
        "summary": {
            "total_tasks": len(categorized),
            "actionable_tasks": actionable_tasks,
            "category_counts": category_counts,
        },
        "execution_order": [
            category
            for category, _priority in sorted(
                _CATEGORY_PRIORITY.items(),
                key=lambda item: item[1],
            )
        ],
        "batches": batches,
        "tasks": categorized,
    }


__all__ = [
    "PLAN_SCHEMA_VERSION",
    "_default_plan_output_path",
    "build_architecture_debt_execution_plan",
    "find_latest_architecture_debt_tasks_file",
    "load_architecture_debt_tasks",
]
