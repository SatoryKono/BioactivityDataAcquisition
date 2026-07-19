"""Artifact-backed task generation for architecture debt closeout planning."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from bioetl.infrastructure.quality.architecture_debt_task_policy import (
    COMMON_ACCEPTANCE_CRITERIA,
    COMMON_ALLOWED_PATHS,
    COMMON_FORBIDDEN_PATHS,
    artifact_checks,
    load_json_if_present,
    load_yaml_if_present,
)


def artifact_defaults(project_root: Path) -> dict[str, Path]:
    quality_root = project_root / "reports" / "quality"
    return {
        "compatibility_census": quality_root / "compatibility-importer-census.json",
        "duplication_baseline": quality_root / "full-app-duplication-baseline.json",
        "hotspot_baseline": quality_root / "hotspot-family-baseline.json",
        "dead_code_inventory": quality_root / "dead-code-inventory.json",
        "debt_scorecard": project_root / "configs" / "quality" / "debt_scorecard.yaml",
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
        current_value - limit_value if isinstance(limit_value, int) else current_value
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
        "checks": artifact_checks(task_family),
        "notes": notes,
        "source_artifact": source_artifact,
    }


def _metric_policy(
    metrics: dict[str, object],
    metric_name: str,
) -> dict[str, object]:
    policy = metrics.get(metric_name, {})
    return cast(dict[str, object], policy) if isinstance(policy, dict) else {}


def _append_reviewed_metric_task(
    tasks: list[dict[str, object]],
    *,
    task_id: str,
    registry_key: str,
    policy: dict[str, object],
    current_value: int,
    limit_field: str,
    goal: str,
    notes: list[str],
    source_artifact: str = "configs/quality/debt_scorecard.yaml",
) -> None:
    if limit_field not in policy:
        return
    limit_value = int(policy[limit_field])  # type: ignore[call-overload]
    if current_value <= limit_value:
        return
    tasks.append(
        _build_artifact_task(
            task_id=task_id,
            task_family="compatibility_surface",
            registry_key=registry_key,
            owner=policy.get("owner", "@bioetl-architecture"),
            current_value=current_value,
            limit_value=limit_value,
            target_file=None,
            source_artifact=source_artifact,
            goal=goal,
            notes=notes,
        )
    )


def build_compatibility_surface_tasks(
    *,
    artifact_paths: dict[str, Path],
) -> list[dict[str, object]]:
    census = load_json_if_present(artifact_paths["compatibility_census"])
    if not census:
        return []
    summary = cast(dict[str, object], census.get("summary", {}))
    scorecard = load_yaml_if_present(artifact_paths["debt_scorecard"])
    compatibility_governance = cast(
        dict[str, object],
        scorecard.get("compatibility_debt_metrics", {}),
    )
    compatibility_metrics = cast(
        dict[str, object], compatibility_governance.get("metrics", {})
    )
    public_governance = cast(
        dict[str, object],
        scorecard.get("sanctioned_public_entrypoint_governance", {}),
    )
    public_metrics = cast(dict[str, object], public_governance.get("metrics", {}))
    tasks: list[dict[str, object]] = []

    for task_id, metric_name, limit_field in (
        ("ARD-COMPAT-001", "transition_compat_count", "target_count"),
        ("ARD-COMPAT-002", "sunset_compat_count", "target_count"),
        ("ARD-COMPAT-003", "expired_compat_count", "max_count"),
    ):
        policy = _metric_policy(compatibility_metrics, metric_name)
        current_value = int(policy.get("current_count", 0))  # type: ignore[call-overload]
        _append_reviewed_metric_task(
            tasks,
            task_id=task_id,
            registry_key=f"compatibility_debt_metrics.{metric_name}",
            policy=policy,
            current_value=current_value,
            limit_field=limit_field,
            goal=(
                "Сократить рассмотренный transition/sunset compatibility debt до "
                "утверждённого target без затрагивания постоянного публичного API."
            ),
            notes=[f"{metric_name}={current_value}"],
        )

    public_entrypoint_count = int(  # type: ignore[call-overload]
        summary.get(
            "sanctioned_public_entrypoint_count",
            summary.get("retained_entrypoint_count", 0),
        )
    )
    _append_reviewed_metric_task(
        tasks,
        task_id="ARD-COMPAT-004",
        registry_key="sanctioned_public_entrypoint_governance.public_entrypoint_count",
        policy=_metric_policy(public_metrics, "public_entrypoint_count"),
        current_value=public_entrypoint_count,
        limit_field="current_count",
        goal=(
            "Устранить нерецензированный рост санкционированных public entrypoint seams."
        ),
        notes=[
            f"live_public_entrypoint_count={public_entrypoint_count}",
            "Reviewed permanent public API remains informational while count is flat.",
        ],
        source_artifact="reports/quality/compatibility-importer-census.json",
    )

    public_export_count = int(  # type: ignore[call-overload]
        summary.get(
            "sanctioned_public_export_facade_count",
            summary.get("retained_public_export_facade_count", 0),
        )
    )
    _append_reviewed_metric_task(
        tasks,
        task_id="ARD-COMPAT-005",
        registry_key=(
            "sanctioned_public_entrypoint_governance.public_export_facade_count"
        ),
        policy=_metric_policy(public_metrics, "public_export_facade_count"),
        current_value=public_export_count,
        limit_field="current_count",
        goal="Устранить нерецензированный рост public export facade seams.",
        notes=[
            f"live_public_export_facade_count={public_export_count}",
            "Reviewed permanent public export facades are not compatibility debt.",
        ],
        source_artifact="reports/quality/compatibility-importer-census.json",
    )

    conflict_count = max(  # type: ignore[call-overload]
        int(summary.get("retained_public_export_facades_with_duplicate_exports", 0)),  # type: ignore[call-overload]
        int(summary.get("retained_public_export_facades_with_resolution_conflicts", 0)),  # type: ignore[call-overload]
        int(  # type: ignore[call-overload]
            summary.get("retained_public_export_facades_with_wrapper_contract_drift", 0)
        ),
    )
    _append_reviewed_metric_task(
        tasks,
        task_id="ARD-COMPAT-006",
        registry_key=(
            "sanctioned_public_entrypoint_governance."
            "public_export_facade_conflict_count"
        ),
        policy=_metric_policy(public_metrics, "public_export_facade_conflict_count"),
        current_value=conflict_count,
        limit_field="current_count",
        goal="Устранить конфликт или drift в санкционированном public export facade.",
        notes=[f"live_public_export_facade_conflict_count={conflict_count}"],
        source_artifact="reports/quality/compatibility-importer-census.json",
    )
    return tasks


def build_duplication_tasks(
    *,
    artifact_paths: dict[str, Path],
) -> list[dict[str, object]]:
    baseline = load_json_if_present(artifact_paths["duplication_baseline"])
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
                str(item.get("category"))  # type: ignore[arg-type]
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


def build_hotspot_family_tasks(
    *,
    artifact_paths: dict[str, Path],
) -> list[dict[str, object]]:
    baseline = load_json_if_present(artifact_paths["hotspot_baseline"])
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
            str(path_prefixes[0])
            if isinstance(path_prefixes, list) and path_prefixes
            else None
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


def build_dead_code_review_tasks(
    *,
    artifact_paths: dict[str, Path],
) -> list[dict[str, object]]:
    inventory = load_json_if_present(artifact_paths["dead_code_inventory"])
    if not inventory:
        return []
    summary = cast(dict[str, object], inventory.get("summary", {}))
    review_window = cast(dict[str, object], inventory.get("review_window", {}))
    untriaged_candidates = int(  # type: ignore[call-overload]
        summary.get("repo_wide_untriaged_zero_import_candidate_count", 0)
    )
    scorecard = load_yaml_if_present(artifact_paths["debt_scorecard"])
    retirement_governance = cast(
        dict[str, object], scorecard.get("retirement_governance_metrics", {})
    )
    retirement_metrics = cast(
        dict[str, object], retirement_governance.get("metrics", {})
    )
    policy = _metric_policy(
        retirement_metrics,
        "repo_wide_untriaged_zero_import_candidate_count",
    )
    reviewed_limit = policy.get(
        "max_count",
        review_window.get("max_untriaged_zero_import_candidates"),
    )
    if not isinstance(reviewed_limit, int):
        return []
    limit_value = reviewed_limit
    if untriaged_candidates <= limit_value:
        return []
    return [
        _build_artifact_task(
            task_id="ARD-DEAD-001",
            task_family="dead_code_review",
            registry_key="repo_wide_untriaged_zero_import_candidate_count",
            owner=policy.get("owner", "@bioetl-architecture"),
            current_value=untriaged_candidates,
            limit_value=limit_value,
            target_file=None,
            source_artifact="reports/quality/dead-code-inventory.json",
            goal=(
                "Продолжить review/removal wave по zero-import candidate surfaces "
                "без роста untriaged residual."
            ),
            notes=[
                (
                    "repo_wide_untriaged_zero_import_candidate_count="
                    f"{untriaged_candidates}"
                ),
                f"review_mode={review_window.get('mode', 'unknown')}",
                "Classified canonical owners and module entrypoints are excluded.",
            ],
        )
    ]


__all__ = [
    "artifact_defaults",
    "build_compatibility_surface_tasks",
    "build_dead_code_review_tasks",
    "build_duplication_tasks",
    "build_hotspot_family_tasks",
]
