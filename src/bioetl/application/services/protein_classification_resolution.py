"""Application service for target protein classification hierarchy resolution."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from bioetl.domain.ports.protein_classification import ProteinClassificationPort
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassificationResolutionError,
)

__all__ = [
    "ProteinClassificationDQIssue",
    "ProteinClassificationResolution",
    "ProteinClassificationResolutionResult",
    "ProteinClassificationResolutionService",
    "ResolveProteinClassificationUseCase",
    "TargetProteinClassificationRecord",
]

_STATUS_MISSING = "missing_classification"
_STATUS_QUARANTINED = "quarantined"
_STATUS_RESOLVED = "resolved"


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

    @classmethod
    def missing(cls, target_id: str) -> TargetProteinClassificationRecord:
        """Build a sentinel row for targets without classification evidence."""
        return cls(
            target_id=target_id,
            classification_status=_STATUS_MISSING,
        )

    @classmethod
    def quarantined(
        cls,
        target_id: str,
    ) -> TargetProteinClassificationRecord:
        """Build a sentinel row for targets whose classification failed DQ."""
        return cls(
            target_id=target_id,
            classification_status=_STATUS_QUARANTINED,
        )

    @classmethod
    def resolved(
        cls,
        *,
        target_id: str,
        component_id: int,
        hierarchy: ProteinClassHierarchy,
    ) -> TargetProteinClassificationRecord:
        """Project a hierarchy into a Gold relation row."""
        levels = hierarchy.levels
        return cls(
            target_id=target_id,
            component_id=component_id,
            leaf_id=hierarchy.leaf_id,
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
        )

    def to_dict(self) -> dict[str, object]:
        """Return a plain dictionary suitable for DataFrame/Gold publication."""
        return {
            "target_id": self.target_id,
            "classification_status": self.classification_status,
            "component_id": self.component_id,
            "leaf_id": self.leaf_id,
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
        invalid_record_policy: str = "quarantine",
    ) -> None:
        self._classification_port = classification_port
        self._invalid_record_policy = invalid_record_policy

    def resolve_target(
        self,
        *,
        target_id: str,
        component_ids: Iterable[int | None],
    ) -> ProteinClassificationResolutionResult:
        """Resolve all protein classifications for one target."""
        normalized_component_ids = _normalize_component_ids(component_ids)
        if not normalized_component_ids:
            return _missing_resolution(target_id)

        by_leaf_id, dq_issues = _collect_target_hierarchies(
            classification_port=self._classification_port,
            component_ids=normalized_component_ids,
        )

        if by_leaf_id:
            return _resolved_resolution(target_id, by_leaf_id, dq_issues)

        return _unresolved_resolution(
            target_id=target_id,
            dq_issues=dq_issues,
            invalid_record_policy=self._invalid_record_policy,
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


def _missing_resolution(target_id: str) -> ProteinClassificationResolutionResult:
    """Build a resolution for targets without any classification candidates."""
    return ProteinClassificationResolutionResult(
        target_id=target_id,
        rows=(TargetProteinClassificationRecord.missing(target_id),),
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
        _record_component_hierarchies(
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


def _record_component_hierarchies(
    *,
    by_leaf_id: dict[int, tuple[int, ProteinClassHierarchy]],
    component_id: int,
    hierarchies: tuple[ProteinClassHierarchy, ...],
) -> None:
    """Keep the lowest component ID for each resolved classification leaf."""
    for hierarchy in hierarchies:
        current = by_leaf_id.get(hierarchy.leaf_id)
        if current is None or component_id < current[0]:
            by_leaf_id[hierarchy.leaf_id] = (component_id, hierarchy)


def _resolved_resolution(
    target_id: str,
    by_leaf_id: dict[int, tuple[int, ProteinClassHierarchy]],
    dq_issues: list[ProteinClassificationDQIssue],
) -> ProteinClassificationResolutionResult:
    """Build resolved relation rows from deduplicated hierarchy candidates."""
    rows = tuple(
        TargetProteinClassificationRecord.resolved(
            target_id=target_id,
            component_id=component_id,
            hierarchy=hierarchy,
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
    invalid_record_policy: str,
) -> ProteinClassificationResolutionResult:
    """Build missing/quarantined fallback rows when no hierarchy was resolved."""
    row_factory = (
        TargetProteinClassificationRecord.quarantined
        if dq_issues and invalid_record_policy == "quarantine"
        else TargetProteinClassificationRecord.missing
    )
    return ProteinClassificationResolutionResult(
        target_id=target_id,
        rows=(row_factory(target_id),),
        dq_issues=tuple(dq_issues),
    )


ProteinClassificationResolution = ProteinClassificationResolutionResult
ResolveProteinClassificationUseCase = ProteinClassificationResolutionService
