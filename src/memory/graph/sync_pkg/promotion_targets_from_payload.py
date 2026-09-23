"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_string_list, _coerce_int
from memory.graph.sync_pkg._core_models import (
    ComplexityAnalysisConfig,
    NodeKey,
    RetirementAnalysisConfig,
)
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _configured_duplicate_families,
)
from memory.graph.sync_pkg.graph_contexts import DuplicateFamilyConfig
from memory.graph.sync_pkg.int_node_property import _casefolded_markers
from memory.graph.sync_pkg.mapping_io import _mapping_section

__all__ = [
    "_complexity_analysis_config",
    "_configured_duplication_families",
    "_duplicate_family_config",
    "_promotion_targets_from_payload",
    "_retirement_analysis_config",
]


def _promotion_targets_from_payload(raw_targets: object) -> tuple[NodeKey, ...]:
    if not isinstance(raw_targets, list):
        return ()
    promotion_targets: list[NodeKey] = []
    for raw_target in raw_targets:
        if not isinstance(raw_target, dict):
            continue
        label = str(raw_target.get("label", "")).strip()
        name = str(raw_target.get("name", "")).strip()
        if label and name:
            promotion_targets.append(NodeKey(label, name))
    return tuple(promotion_targets)


def _duplicate_family_config(
    name: object, payload: object
) -> DuplicateFamilyConfig | None:
    if not isinstance(payload, dict):
        return None
    roots = tuple(_as_string_list(payload.get("roots")))
    package_family = str(payload.get("package_family", "")).strip()
    if not roots or not package_family:
        return None
    excluded_paths = tuple(sorted(set(_as_string_list(payload.get("excluded_paths")))))
    return DuplicateFamilyConfig(
        name=str(name),
        roots=roots,
        package_family=package_family,
        promotion_targets=_promotion_targets_from_payload(
            payload.get("promotion_targets", [])
        ),
        excluded_paths=excluded_paths,
    )


def _configured_duplication_families(
    raw_families: object,
) -> list[DuplicateFamilyConfig]:
    if not isinstance(raw_families, dict):
        return []
    families: list[DuplicateFamilyConfig] = []
    for family_name, family_payload in raw_families.items():
        family = _duplicate_family_config(family_name, family_payload)
        if family is not None:
            families.append(family)
    return families


def _retirement_analysis_config(
    memory_mapping: dict[str, object],
    duplication_config: dict[str, object],
) -> RetirementAnalysisConfig:
    payload = _mapping_section(memory_mapping, "retirement_analysis")
    family_names = _configured_duplicate_families(payload, duplication_config)

    return RetirementAnalysisConfig(
        enabled=bool(payload.get("enabled", True)),
        family_names=family_names,
        current_cycle_age_days=_coerce_int(
            payload.get("current_cycle_age_days", 45), 45
        ),
        stale_age_days=_coerce_int(payload.get("stale_age_days", 180), 180),
        dead_score_threshold=_coerce_int(payload.get("dead_score_threshold", 6), 6),
        wip_markers=_casefolded_markers(
            payload,
            "wip_markers",
            ["todo", "wip", "follow-up", "phase 2", "spike", "temporary"],
        ),
        deprecation_markers=_casefolded_markers(
            payload,
            "deprecation_markers",
            [
                "deprecated",
                "legacy",
                "obsolete",
                "compat",
                "remove after",
                "migration shim",
            ],
        ),
    )


def _complexity_analysis_config(
    memory_mapping: dict[str, object],
    duplication_config: dict[str, object],
    retirement_config: RetirementAnalysisConfig,
) -> ComplexityAnalysisConfig:
    payload = _mapping_section(memory_mapping, "complexity_analysis")
    family_names = _configured_duplicate_families(payload, duplication_config)

    return ComplexityAnalysisConfig(
        enabled=bool(payload.get("enabled", True)),
        family_names=family_names or retirement_config.family_names,
        complexity_score_threshold=_coerce_int(
            payload.get("complexity_score_threshold", 4), 4
        ),
        removable_score_threshold=_coerce_int(
            payload.get("removable_score_threshold", 7), 7
        ),
        indirection_markers=_casefolded_markers(
            payload,
            "indirection_markers",
            [
                "helper",
                "helpers",
                "mixin",
                "policy",
                "codec",
                "compat",
                "legacy",
                "wrapper",
                "shim",
            ],
        ),
        stateful_markers=_casefolded_markers(
            payload,
            "stateful_markers",
            ["checkpoint", "resume", "state", "fsm", "transition", "runner"],
        ),
        deprecation_markers=retirement_config.deprecation_markers,
        blocker_anchor_limit=_coerce_int(payload.get("blocker_anchor_limit", 3), 3),
    )
