"""Collaborator bundle and legacy wiring bridge for ``MergeService``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.coalesce_policy import CoalescePolicyService
    from bioetl.application.composite.column_orderer import ColumnOrderer
    from bioetl.application.composite.column_priority_orderer import (
        ColumnPriorityOrderer,
    )
    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.application.composite.join_planner import JoinPlannerService

__all__ = ["MergeCollaboratorGroup", "build_merge_collaborators"]


@dataclass(frozen=True, slots=True)
class MergeCollaboratorGroup:
    """Bundle of merge-time collaborators wired in composition."""

    deduplicator: EnricherDeduplicatorService
    aggregator: EnricherAggregator
    renamer: ColumnRenamer
    orderer: ColumnOrderer
    priority_orderer: ColumnPriorityOrderer
    coalesce_policy: CoalescePolicyService
    conflict_resolver: ConflictResolverService
    join_planner: JoinPlannerService


# ``MergeService`` still accepts the legacy keyword-only collaborator form during
# the phased migration to ``MergeCollaboratorGroup``.
_LEGACY_COLLABORATOR_KEYS = frozenset(
    {
        "deduplicator",
        "aggregator",
        "renamer",
        "orderer",
        "priority_orderer",
        "coalesce_policy",
        "conflict_resolver",
        "join_planner",
    }
)


def build_merge_collaborators(
    *,
    collaborators: MergeCollaboratorGroup | None,
    legacy_collaborators: dict[str, Any],  # Any: phased compatibility bridge
) -> MergeCollaboratorGroup:
    """Normalize new bundle-style wiring and legacy keyword collaborators."""
    if collaborators is not None:
        if legacy_collaborators:
            unexpected = sorted(legacy_collaborators)
            raise TypeError(
                "MergeService received both collaborator group and legacy "
                f"keyword collaborators: {unexpected}"
            )
        return collaborators

    missing = sorted(_LEGACY_COLLABORATOR_KEYS.difference(legacy_collaborators))
    unexpected = sorted(set(legacy_collaborators).difference(_LEGACY_COLLABORATOR_KEYS))
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        raise TypeError(
            "MergeService requires collaborators=MergeCollaboratorGroup(...) or the "
            f"full legacy collaborator keyword set ({', '.join(details)})"
        )

    return MergeCollaboratorGroup(
        deduplicator=legacy_collaborators["deduplicator"],
        aggregator=legacy_collaborators["aggregator"],
        renamer=legacy_collaborators["renamer"],
        orderer=legacy_collaborators["orderer"],
        priority_orderer=legacy_collaborators["priority_orderer"],
        coalesce_policy=legacy_collaborators["coalesce_policy"],
        conflict_resolver=legacy_collaborators["conflict_resolver"],
        join_planner=legacy_collaborators["join_planner"],
    )
