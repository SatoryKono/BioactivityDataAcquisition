"""Application service for target protein classification hierarchy resolution."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from bioetl.application.services.protein._classification_resolution_support import (
    json_array,
    record_component_hierarchies,
)
from bioetl.domain.mapping.protein_class_target_type import (
    PROTEIN_CLASS_TARGET_TYPE_RULE_VERSION,
    ProteinClassTargetTypeMappingData,
    current_protein_class_target_type_mapping,
    normalize_protein_class_top_level,
)
from bioetl.domain.ports import ProteinClassificationPort
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassificationResolutionError,
)

__all__ = [
    "InvalidRecordPolicy",
    "ProteinClassificationDQIssue",
    "ProteinClassificationResolutionResult",
    "ProteinClassificationResolutionService",
    "TargetProteinClassificationRecord",
]

_STATUS_MISSING = "missing_classification"
_STATUS_QUARANTINED = "quarantined"
_STATUS_RESOLVED = "resolved"
InvalidRecordPolicy = Literal["quarantine", "missing"]
_INVALID_RECORD_POLICIES: frozenset[str] = frozenset({"quarantine", "missing"})


@dataclass(frozen=True, slots=True)
class ProteinClassificationDQIssue:
    """DQ issue raised while resolving target protein classifications."""

    component_id: int | None
    error_code: str
    message: str


@dataclass(frozen=True, slots=True)
class TargetProteinClassificationRecord:
    """Gold-facing target protein classification relation row."""

    target_id: str
    classification_status: str
    component_id: int | None = None
    leaf_id: int | None = None
    path_ids: str | None = None
    path_names: str | None = None
    path_labels: str | None = None
    depth: int | None = None
    root_id: int | None = None
    is_leaf: bool | None = None
    l1_id: int | None = None
    l1_name: str | None = None
    l1_desc: str | None = None
    l2_id: int | None = None
    l2_name: str | None = None
    l2_desc: str | None = None
    l3_id: int | None = None
    l3_name: str | None = None
    l3_desc: str | None = None
    l4_id: int | None = None
    l4_name: str | None = None
    l4_desc: str | None = None
    l5_id: int | None = None
    l5_name: str | None = None
    l5_desc: str | None = None
    canonical_l1: str | None = None
    l1_counts_for_target_type: bool | None = None
    l1_mapping_version: str | None = None
    target_type_rule_version: str | None = None
    l1_normalization_status: str | None = None
    l1_normalization_notes: str | None = None

    @classmethod
    def missing(
        cls,
        target_id: str,
        *,
        mapping_version: str | None = None,
    ) -> TargetProteinClassificationRecord:
        """Build a sentinel row for targets without classification evidence."""
        return cls(
            target_id=target_id,
            classification_status=_STATUS_MISSING,
            canonical_l1="missing",
            l1_counts_for_target_type=False,
            l1_mapping_version=mapping_version,
            target_type_rule_version=PROTEIN_CLASS_TARGET_TYPE_RULE_VERSION,
            l1_normalization_status="missing",
            l1_normalization_notes="no resolved protein classification evidence",
        )

    @classmethod
    def quarantined(
        cls,
        target_id: str,
        *,
        mapping_version: str | None = None,
    ) -> TargetProteinClassificationRecord:
        """Build a sentinel row for targets whose classification failed DQ."""
        return cls(
            target_id=target_id,
            classification_status=_STATUS_QUARANTINED,
            canonical_l1="missing",
            l1_counts_for_target_type=False,
            l1_mapping_version=mapping_version,
            target_type_rule_version=PROTEIN_CLASS_TARGET_TYPE_RULE_VERSION,
            l1_normalization_status="failed",
            l1_normalization_notes="classification hierarchy failed DQ resolution",
        )

    @classmethod
    def resolved(
        cls,
        *,
        target_id: str,
        component_id: int,
        hierarchy: ProteinClassHierarchy,
        mapping_data: ProteinClassTargetTypeMappingData,
    ) -> TargetProteinClassificationRecord:
        """Project a hierarchy into a Gold relation row."""
        levels = hierarchy.levels
        normalized_l1 = normalize_protein_class_top_level(
            levels[0].name,
            mapping_data,
        )
        return cls(
            target_id=target_id,
            component_id=component_id,
            leaf_id=hierarchy.leaf_id,
            path_ids=json_array(hierarchy.path_ids),
            path_names=json_array(hierarchy.path_names),
            path_labels=json_array(hierarchy.path_labels),
            depth=hierarchy.depth,
            root_id=hierarchy.root_id,
            is_leaf=hierarchy.is_leaf,
            classification_status=_STATUS_RESOLVED,
            l1_id=levels[0].id,
            l1_name=levels[0].name,
            l1_desc=levels[0].desc,
            l2_id=levels[1].id,
            l2_name=levels[1].name,
            l2_desc=levels[1].desc,
            l3_id=levels[2].id,
            l3_name=levels[2].name,
            l3_desc=levels[2].desc,
            l4_id=levels[3].id,
            l4_name=levels[3].name,
            l4_desc=levels[3].desc,
            l5_id=levels[4].id,
            l5_name=levels[4].name,
            l5_desc=levels[4].desc,
            canonical_l1=normalized_l1.canonical_l1,
            l1_counts_for_target_type=normalized_l1.counts_for_target_type,
            l1_mapping_version=mapping_data.mapping_version,
            target_type_rule_version=PROTEIN_CLASS_TARGET_TYPE_RULE_VERSION,
            l1_normalization_status=normalized_l1.normalization_status,
            l1_normalization_notes=normalized_l1.normalization_notes,
        )

    def to_dict(self) -> dict[str, object]:
        """Return a plain dictionary suitable for DataFrame/Gold publication."""
        return {
            "target_id": self.target_id,
            "classification_status": self.classification_status,
            "component_id": self.component_id,
            "leaf_id": self.leaf_id,
            "path_ids": self.path_ids,
            "path_names": self.path_names,
            "path_labels": self.path_labels,
            "depth": self.depth,
            "root_id": self.root_id,
            "is_leaf": self.is_leaf,
            "l1_id": self.l1_id,
            "l1_name": self.l1_name,
            "l1_desc": self.l1_desc,
            "l2_id": self.l2_id,
            "l2_name": self.l2_name,
            "l2_desc": self.l2_desc,
            "l3_id": self.l3_id,
            "l3_name": self.l3_name,
            "l3_desc": self.l3_desc,
            "l4_id": self.l4_id,
            "l4_name": self.l4_name,
            "l4_desc": self.l4_desc,
            "l5_id": self.l5_id,
            "l5_name": self.l5_name,
            "l5_desc": self.l5_desc,
            "canonical_l1": self.canonical_l1,
            "l1_counts_for_target_type": self.l1_counts_for_target_type,
            "l1_mapping_version": self.l1_mapping_version,
            "target_type_rule_version": self.target_type_rule_version,
            "l1_normalization_status": self.l1_normalization_status,
            "l1_normalization_notes": self.l1_normalization_notes,
        }


@dataclass(frozen=True, slots=True)
class ProteinClassificationResolutionResult:
    """Resolution result for one target."""

    target_id: str
    rows: tuple[TargetProteinClassificationRecord, ...]
    dq_issues: tuple[ProteinClassificationDQIssue, ...] = ()

    @property
    def has_quarantine(self) -> bool:
        """Return True when resolution encountered hard DQ issues."""
        return bool(self.dq_issues)


class ProteinClassificationResolutionService:
    """Resolve deterministic L1-L5 protein classification rows for a target."""

    def __init__(
        self,
        classification_port: ProteinClassificationPort,
        *,
        invalid_record_policy: InvalidRecordPolicy = "quarantine",
        target_type_mapping_data: ProteinClassTargetTypeMappingData | None = None,
    ) -> None:
        if invalid_record_policy not in _INVALID_RECORD_POLICIES:
            raise ValueError(
                "invalid_record_policy must be one of "
                f"{sorted(_INVALID_RECORD_POLICIES)}, got {invalid_record_policy!r}"
            )
        self._classification_port = classification_port
        self._invalid_record_policy = invalid_record_policy
        self._target_type_mapping_data = (
            target_type_mapping_data or current_protein_class_target_type_mapping()
        )

    def resolve_target(
        self,
        *,
        target_id: str,
        component_ids: Iterable[int | None],
    ) -> ProteinClassificationResolutionResult:
        """Resolve all protein classifications for one target."""
        normalized_component_ids = _normalize_component_ids(component_ids)
        if not normalized_component_ids:
            return _missing_resolution(
                target_id,
                mapping_version=self._target_type_mapping_data.mapping_version,
            )

        by_leaf_id, dq_issues = _collect_target_hierarchies(
            classification_port=self._classification_port,
            component_ids=normalized_component_ids,
        )

        if by_leaf_id:
            return _resolved_resolution(
                target_id,
                by_leaf_id,
                dq_issues,
                mapping_data=self._target_type_mapping_data,
            )

        return _unresolved_resolution(
            target_id=target_id,
            dq_issues=dq_issues,
            invalid_record_policy=self._invalid_record_policy,
            mapping_version=self._target_type_mapping_data.mapping_version,
        )


def _normalize_component_ids(component_ids: Iterable[int | None]) -> tuple[int, ...]:
    """Return positive component IDs in deterministic order."""
    normalized = {
        component_id
        for component_id in component_ids
        if isinstance(component_id, int) and not isinstance(component_id, bool)
        if component_id > 0
    }
    return tuple(sorted(normalized))


def _missing_resolution(
    target_id: str,
    *,
    mapping_version: str | None,
) -> ProteinClassificationResolutionResult:
    """Build a resolution for targets without any classification candidates."""
    return ProteinClassificationResolutionResult(
        target_id=target_id,
        rows=(
            TargetProteinClassificationRecord.missing(
                target_id,
                mapping_version=mapping_version,
            ),
        ),
    )


def _collect_target_hierarchies(
    *,
    classification_port: ProteinClassificationPort,
    component_ids: tuple[int, ...],
) -> tuple[
    dict[int, tuple[int, ProteinClassHierarchy]],
    list[ProteinClassificationDQIssue],
]:
    """Collect deduplicated leaf hierarchies and DQ issues for target components."""
    by_leaf_id: dict[int, tuple[int, ProteinClassHierarchy]] = {}
    dq_issues: list[ProteinClassificationDQIssue] = []
    for component_id in component_ids:
        hierarchies, issue = _load_component_hierarchies(
            classification_port=classification_port,
            component_id=component_id,
        )
        if issue is not None:
            dq_issues.append(issue)
            continue
        record_component_hierarchies(
            by_leaf_id=by_leaf_id,
            component_id=component_id,
            hierarchies=hierarchies,
        )
    return by_leaf_id, dq_issues


def _load_component_hierarchies(
    *,
    classification_port: ProteinClassificationPort,
    component_id: int,
) -> tuple[tuple[ProteinClassHierarchy, ...], ProteinClassificationDQIssue | None]:
    """Load classifications for one component, converting failures to DQ issues."""
    try:
        hierarchies = classification_port.get_component_classifications(component_id)
    except ProteinClassificationResolutionError as exc:
        return (), _resolution_failure_issue(component_id=component_id, error=exc)
    return tuple(hierarchies), None


def _resolution_failure_issue(
    *,
    component_id: int,
    error: ProteinClassificationResolutionError,
) -> ProteinClassificationDQIssue:
    """Build a DQ issue for a failed component classification lookup."""
    return ProteinClassificationDQIssue(
        component_id=component_id,
        error_code="protein_classification_resolution_failed",
        message=str(error),
    )


def _resolved_resolution(
    target_id: str,
    by_leaf_id: dict[int, tuple[int, ProteinClassHierarchy]],
    dq_issues: list[ProteinClassificationDQIssue],
    *,
    mapping_data: ProteinClassTargetTypeMappingData,
) -> ProteinClassificationResolutionResult:
    """Build resolved relation rows from deduplicated hierarchy candidates."""
    rows = tuple(
        TargetProteinClassificationRecord.resolved(
            target_id=target_id,
            component_id=component_id,
            hierarchy=hierarchy,
            mapping_data=mapping_data,
        )
        for _leaf_id, (component_id, hierarchy) in sorted(by_leaf_id.items())
    )
    return ProteinClassificationResolutionResult(
        target_id=target_id,
        rows=rows,
        dq_issues=tuple(dq_issues),
    )


def _unresolved_resolution(
    *,
    target_id: str,
    dq_issues: list[ProteinClassificationDQIssue],
    invalid_record_policy: InvalidRecordPolicy,
    mapping_version: str | None,
) -> ProteinClassificationResolutionResult:
    """Build missing/quarantined fallback rows when no hierarchy was resolved."""
    row_factory = (
        TargetProteinClassificationRecord.quarantined
        if dq_issues and invalid_record_policy == "quarantine"
        else TargetProteinClassificationRecord.missing
    )
    return ProteinClassificationResolutionResult(
        target_id=target_id,
        rows=(row_factory(target_id, mapping_version=mapping_version),),
        dq_issues=tuple(dq_issues),
    )


ProteinClassificationResolution = ProteinClassificationResolutionResult
ResolveProteinClassificationUseCase = ProteinClassificationResolutionService
