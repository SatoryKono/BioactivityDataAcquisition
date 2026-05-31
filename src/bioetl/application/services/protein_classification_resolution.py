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
    hierarchy_index: int
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
            hierarchy_index=0,
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
            hierarchy_index=0,
            classification_status=_STATUS_QUARANTINED,
        )

    @classmethod
    def resolved(
        cls,
        *,
        target_id: str,
        hierarchy_index: int,
        component_id: int,
        hierarchy: ProteinClassHierarchy,
    ) -> TargetProteinClassificationRecord:
        """Project a hierarchy into a Gold relation row."""
        levels = hierarchy.levels
        return cls(
            target_id=target_id,
            component_id=component_id,
            hierarchy_index=hierarchy_index,
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
            "component_id": self.component_id,
            "hierarchy_index": self.hierarchy_index,
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
            "classification_status": self.classification_status,
        }


@dataclass(frozen=True, slots=True)
class ProteinClassificationResolution:
    """Resolution result for one target."""

    target_id: str
    rows: tuple[TargetProteinClassificationRecord, ...]
    dq_issues: tuple[ProteinClassificationDQIssue, ...] = ()

    @property
    def has_quarantine(self) -> bool:
        """Return True when resolution encountered hard DQ issues."""
        return bool(self.dq_issues)


class ResolveProteinClassificationUseCase:
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
    ) -> ProteinClassificationResolution:
        """Resolve all protein classifications for one target."""
        normalized_component_ids = _normalize_component_ids(component_ids)
        if not normalized_component_ids:
            return ProteinClassificationResolution(
                target_id=target_id,
                rows=(TargetProteinClassificationRecord.missing(target_id),),
            )

        by_leaf_id: dict[int, tuple[int, ProteinClassHierarchy]] = {}
        dq_issues: list[ProteinClassificationDQIssue] = []
        for component_id in normalized_component_ids:
            try:
                hierarchies = self._classification_port.get_component_classifications(
                    component_id
                )
            except ProteinClassificationResolutionError as exc:
                dq_issues.append(
                    ProteinClassificationDQIssue(
                        component_id=component_id,
                        error_code="protein_classification_resolution_failed",
                        message=str(exc),
                    )
                )
                continue

            for hierarchy in hierarchies:
                current = by_leaf_id.get(hierarchy.leaf_id)
                if current is None or component_id < current[0]:
                    by_leaf_id[hierarchy.leaf_id] = (component_id, hierarchy)

        if by_leaf_id:
            rows = tuple(
                TargetProteinClassificationRecord.resolved(
                    target_id=target_id,
                    hierarchy_index=index,
                    component_id=component_id,
                    hierarchy=hierarchy,
                )
                for index, (_leaf_id, (component_id, hierarchy)) in enumerate(
                    sorted(by_leaf_id.items())
                )
            )
            return ProteinClassificationResolution(
                target_id=target_id,
                rows=rows,
                dq_issues=tuple(dq_issues),
            )

        if dq_issues and self._invalid_record_policy == "quarantine":
            rows = (TargetProteinClassificationRecord.quarantined(target_id),)
        else:
            rows = (TargetProteinClassificationRecord.missing(target_id),)
        return ProteinClassificationResolution(
            target_id=target_id,
            rows=rows,
            dq_issues=tuple(dq_issues),
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
