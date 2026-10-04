"""Owner-only merge-service assembly for composite support runtime."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING, cast

from bioetl.application.composite.runtime_wiring_api import (
    JoinHow,
    MergeCollaboratorGroup,
    MergeService,
)
from bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder import (
    build_merge_dependencies,
)
from bioetl.domain.composite.strategy import MergeStrategy
from bioetl.domain.normalization.join_keys import JoinKeyNormalizationPolicy

if TYPE_CHECKING:
    from bioetl.application.composite.merger_orchestration import MergeExecutionRequest
    from bioetl.domain.composite.result import MergeResult

    from bioetl.application.composite.runtime_wiring_api import (
        EnrichmentCrossValidator,
    )
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import ClockPort, DeltaReaderPort, LoggerPort

from bioetl.application.ports.storage import (
    CompositeMergeStorageProtocol as _CompositeMergeStorage,
)


SYSTEM_COLUMNS_TO_DROP = frozenset(
    {
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_dq_warn",
        "_dq_error",
        "_index",
        "_lookup_method",
        "_original_id",
        "_source",
    }
)


def _resolve_join_how(strategy: MergeStrategy) -> JoinHow:
    # Unknown strategies default to a left join (fail-open by design,
    # covered by test_resolve_join_how_defaults_unknown_strategy_to_left_join).
    match cast("str", strategy):
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
    delta_reader: DeltaReaderPort,
    field_group_registry: FieldGroupRegistry | None,
    cross_validator: EnrichmentCrossValidator | None,
    logger: LoggerPort,
    system_columns_to_drop: frozenset[str],
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy],
    clock: ClockPort | None = None,
    execution_hook: Callable[
        [
            MergeExecutionRequest,
            Callable[[MergeExecutionRequest], Awaitable[MergeResult]],
        ],
        Awaitable[MergeResult],
    ]
    | None = None,
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
        execution_hook=execution_hook,
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
