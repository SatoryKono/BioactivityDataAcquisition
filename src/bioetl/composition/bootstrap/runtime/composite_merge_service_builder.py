"""Owner-only merge-service assembly for composite support runtime."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.runtime_wiring_api import (
    JoinHow,
    MergeCollaboratorGroup,
    MergeService,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_builders import (
    build_merge_dependencies,
)
from bioetl.domain.composite.strategy import MergeStrategy
from bioetl.domain.normalization.join_keys import JoinKeyNormalizationPolicy
from bioetl.domain.ports import MergedStoragePort, SilverStoragePort

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.composite.runtime_wiring_api import (
        EnrichmentCrossValidator,
    )
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import ClockPort, LoggerPort
    from bioetl.infrastructure.storage.delta_reader import DeltaReader


class _CompositeMergeStorage(MergedStoragePort, SilverStoragePort, Protocol):
    """Storage capabilities required by composite merge assembly."""


def _resolve_join_how(strategy: MergeStrategy) -> JoinHow:
    match strategy:
        case MergeStrategy.LEFT_OUTER:
            return "left"
        case MergeStrategy.INNER:
            return "inner"
        case MergeStrategy.UNION:
            return "full"
        case _:
            return "left"


def build_composite_merge_service(
    *,
    config: CompositeConfig,
    storage: _CompositeMergeStorage,
    resolve_gold_schema: Callable[[str], type | None],
    delta_reader: DeltaReader,
    field_group_registry: FieldGroupRegistry | None,
    cross_validator: EnrichmentCrossValidator | None,
    logger: LoggerPort,
    system_columns_to_drop: frozenset[str],
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy],
    clock: ClockPort | None = None,
) -> MergeService:
    """Build the composite merge service from explicit owner-only collaborators."""
    merge_dependencies = build_merge_dependencies(
        config=config,
        logger=logger,
        resolve_join_how=_resolve_join_how,
        normalization_policies=normalization_policies,
        system_columns_to_drop=system_columns_to_drop,
    )
    return MergeService(
        merge_config=config.merge,
        storage=storage,
        logger=logger,
        delta_reader=delta_reader,
        silver_reader=storage,
        field_group_registry=field_group_registry,
        cross_validator=cross_validator,
        gold_schema=resolve_gold_schema(config.name),
        clock=clock,
        collaborators=MergeCollaboratorGroup(
            deduplicator=merge_dependencies.deduplicator,
            aggregator=merge_dependencies.aggregator,
            renamer=merge_dependencies.renamer,
            order_service=merge_dependencies.order_service,
            coalesce_policy=merge_dependencies.coalesce_policy,
            conflict_resolver=merge_dependencies.conflict_resolver,
            join_planner=merge_dependencies.join_planner,
        ),
    )


__all__ = ["build_composite_merge_service"]
