"""Unit tests for composite support service builder functions."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap.runtime.composite_support_service_builders import (
    build_execution_support_services,
    build_merge_dependencies,
    build_runtime_management_services,
)
from bioetl.domain.composite.strategy import MergeStrategy


def _make_config(
    *,
    quarantine_enabled: bool = False,
    column_groups: tuple[str, ...] | None = None,
) -> Any:
    return cast(
        Any,
        SimpleNamespace(
            name="composite_publication",
            version="1.0.0",
            dq=SimpleNamespace(),
            execution=SimpleNamespace(max_concurrency=3),
            cross_validation=SimpleNamespace(enabled=quarantine_enabled),
            merge=SimpleNamespace(
                strategy=MergeStrategy.LEFT_OUTER,
                column_groups=column_groups,
            ),
        ),
    )


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.EnrichmentCoordinatorService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.DependencyCoordinatorService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.DependencyResultService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.DependencyProgressService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.create_chained_key_resolver"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.create_seed_key_resolver"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.KeyExtractorService"
)
def test_build_execution_support_services_wires_expected_collaborators(
    mock_key_extractor_cls: MagicMock,
    mock_seed_key_resolver: MagicMock,
    mock_chained_key_resolver: MagicMock,
    mock_progress_service_cls: MagicMock,
    mock_result_service_cls: MagicMock,
    mock_dependency_coordinator_cls: MagicMock,
    mock_enrichment_coordinator_cls: MagicMock,
) -> None:
    logger = MagicMock()
    delta_reader = MagicMock()
    key_extractor = MagicMock(name="key_extractor")
    dependency_coordinator = MagicMock(name="dependency_coordinator")
    coordinator = MagicMock(name="coordinator")

    mock_key_extractor_cls.return_value = key_extractor
    mock_dependency_coordinator_cls.return_value = dependency_coordinator
    mock_enrichment_coordinator_cls.return_value = coordinator

    result = build_execution_support_services(
        config=_make_config(),
        logger=logger,
        delta_reader=delta_reader,
    )

    assert result.key_extractor is key_extractor
    assert result.dependency_coordinator is dependency_coordinator
    assert result.coordinator is coordinator
    mock_key_extractor_cls.assert_called_once_with(
        delta_reader=delta_reader,
        logger=logger,
    )
    mock_seed_key_resolver.assert_called_once_with(logger)
    mock_chained_key_resolver.assert_called_once_with(logger)
    mock_progress_service_cls.assert_called_once_with(logger)
    mock_result_service_cls.assert_called_once_with(logger)
    assert (
        mock_dependency_coordinator_cls.call_args.kwargs["delta_reader"] is delta_reader
    )
    assert mock_enrichment_coordinator_cls.call_args.kwargs["dq_config"] is not None


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.FSMStateHelperService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_quarantine_port"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_composite_checkpoint_port"
)
def test_build_runtime_management_services_enables_quarantine_when_configured(
    mock_checkpoint_port: MagicMock,
    mock_quarantine_port: MagicMock,
    mock_fsm_state_helper_cls: MagicMock,
) -> None:
    infra_context = cast(Any, SimpleNamespace(metrics=MagicMock(name="metrics")))
    logger = MagicMock()
    settings = MagicMock()
    runtime = cast(Any, SimpleNamespace(resume=True))
    checkpoint_storage = MagicMock(name="checkpoint_storage")
    quarantine_port = MagicMock(name="quarantine_port")
    checkpoint_manager = MagicMock(name="checkpoint_manager")
    dq_report_service = MagicMock(name="dq_report_service")
    checkpoint_manager_cls = cast(Any, MagicMock(return_value=checkpoint_manager))
    create_dq_report_service = MagicMock(return_value=dq_report_service)
    fsm_state_helper = MagicMock(name="fsm_state_helper")

    mock_checkpoint_port.return_value = checkpoint_storage
    mock_quarantine_port.return_value = quarantine_port
    mock_fsm_state_helper_cls.return_value = fsm_state_helper

    result = build_runtime_management_services(
        config=_make_config(quarantine_enabled=True),
        runtime=runtime,
        infra_context=infra_context,
        settings=settings,
        logger=logger,
        run_id="run-123",
        checkpoint_manager_cls=checkpoint_manager_cls,
        create_dq_report_service=create_dq_report_service,
    )

    assert result.checkpoint_manager is checkpoint_manager
    assert result.dq_report_service is dq_report_service
    assert result.fsm_state_helper is fsm_state_helper
    assert result.quarantine_port is quarantine_port
    mock_checkpoint_port.assert_called_once_with()
    mock_quarantine_port.assert_called_once_with()
    cast(MagicMock, checkpoint_manager_cls).assert_called_once_with(
        composite_name="composite_publication",
        run_id="run-123",
        storage=checkpoint_storage,
        logger=logger,
        resume=True,
        expected_effective_config_hash="",
        expected_contract_ref="composite_publication",
        expected_contract_version="1.0.0",
    )
    create_dq_report_service.assert_called_once_with(
        logger,
        settings,
        infra_context.metrics,
    )


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.FSMStateHelperService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_quarantine_port"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_composite_checkpoint_port"
)
def test_build_runtime_management_services_skips_quarantine_when_disabled(
    mock_checkpoint_port: MagicMock,
    mock_quarantine_port: MagicMock,
    mock_fsm_state_helper_cls: MagicMock,
) -> None:
    infra_context = cast(Any, SimpleNamespace(metrics=MagicMock(name="metrics")))
    checkpoint_manager_cls = cast(Any, MagicMock(return_value=MagicMock()))
    mock_checkpoint_port.return_value = MagicMock()
    mock_fsm_state_helper_cls.return_value = MagicMock()

    result = build_runtime_management_services(
        config=_make_config(quarantine_enabled=False),
        runtime=cast(Any, SimpleNamespace(resume=False)),
        infra_context=infra_context,
        settings=MagicMock(),
        logger=MagicMock(),
        run_id="run-123",
        checkpoint_manager_cls=checkpoint_manager_cls,
        create_dq_report_service=MagicMock(return_value=MagicMock()),
    )

    assert result.quarantine_port is None
    mock_quarantine_port.assert_not_called()


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.FSMStateHelperService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_quarantine_port"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_composite_checkpoint_port"
)
def test_build_runtime_management_services_propagates_config_hash_when_available(
    mock_checkpoint_port: MagicMock,
    mock_quarantine_port: MagicMock,
    mock_fsm_state_helper_cls: MagicMock,
) -> None:
    infra_context = cast(Any, SimpleNamespace(metrics=MagicMock(name="metrics")))
    logger = MagicMock()
    settings = MagicMock()
    runtime = cast(Any, SimpleNamespace(resume=False))
    config = _make_config(quarantine_enabled=False)
    config.to_dict = MagicMock(
        return_value={
            "name": "composite_publication",
            "version": "1.0.0",
            "seed": {"pipeline": "pubmed_publication"},
            "enrichers": [],
            "merge": {"strategy": "left_outer"},
        }
    )
    checkpoint_storage = MagicMock(name="checkpoint_storage")
    checkpoint_manager_cls = cast(Any, MagicMock(return_value=MagicMock()))

    mock_checkpoint_port.return_value = checkpoint_storage
    mock_quarantine_port.return_value = MagicMock(name="quarantine_port")
    mock_fsm_state_helper_cls.return_value = MagicMock(name="fsm_state_helper")

    build_runtime_management_services(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        settings=settings,
        logger=logger,
        run_id="run-123",
        checkpoint_manager_cls=checkpoint_manager_cls,
        create_dq_report_service=MagicMock(return_value=MagicMock()),
    )

    kwargs = cast(MagicMock, checkpoint_manager_cls).call_args.kwargs
    config_hash = kwargs["expected_effective_config_hash"]
    assert isinstance(config_hash, str)
    assert len(config_hash) == 64


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.JoinPlannerService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.DependencyJoinerService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.PolarsJoinAdapter"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.JoinKeyResolverService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.ConflictResolverService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.CoalescePolicyService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.ColumnPriorityOrderer"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.ColumnOrderer"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.ColumnRenamer"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.EnricherAggregator"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.EnricherDeduplicatorService"
)
def test_build_merge_dependencies_wires_join_adapter_and_planner(
    mock_deduplicator_cls: MagicMock,
    mock_aggregator_cls: MagicMock,
    mock_renamer_cls: MagicMock,
    mock_orderer_cls: MagicMock,
    mock_priority_orderer_cls: MagicMock,
    mock_coalesce_policy_cls: MagicMock,
    mock_conflict_resolver_cls: MagicMock,
    mock_join_key_resolver_cls: MagicMock,
    mock_join_adapter_cls: MagicMock,
    mock_dependency_joiner_cls: MagicMock,
    mock_join_planner_cls: MagicMock,
) -> None:
    logger = MagicMock()
    deduplicator = MagicMock(name="deduplicator")
    aggregator = MagicMock(name="aggregator")
    renamer = MagicMock(name="renamer")
    orderer = MagicMock(name="orderer")
    priority_orderer = MagicMock(name="priority_orderer")
    coalesce_policy = MagicMock(name="coalesce_policy")
    conflict_resolver = MagicMock(name="conflict_resolver")
    join_key_resolver = MagicMock(name="join_key_resolver")
    join_executor = MagicMock(name="join_executor")
    dependency_joiner = MagicMock(name="dependency_joiner")
    join_planner = MagicMock(name="join_planner")

    mock_deduplicator_cls.return_value = deduplicator
    mock_aggregator_cls.return_value = aggregator
    mock_renamer_cls.return_value = renamer
    mock_orderer_cls.return_value = orderer
    mock_priority_orderer_cls.return_value = priority_orderer
    mock_coalesce_policy_cls.return_value = coalesce_policy
    mock_conflict_resolver_cls.return_value = conflict_resolver
    mock_join_key_resolver_cls.return_value = join_key_resolver
    mock_join_adapter_cls.return_value = join_executor
    mock_dependency_joiner_cls.return_value = dependency_joiner
    mock_join_planner_cls.return_value = join_planner

    result = build_merge_dependencies(
        config=_make_config(column_groups=("priority",)),
        logger=logger,
        resolve_join_how=lambda strategy: (
            "left" if strategy is MergeStrategy.LEFT_OUTER else "inner"
        ),
        normalize_join_keys=frozenset({"doi", "pmid"}),
        system_columns_to_drop=frozenset({"_run_id"}),
    )

    assert result.deduplicator is deduplicator
    assert result.aggregator is aggregator
    assert result.renamer is renamer
    assert result.orderer is orderer
    assert result.priority_orderer is priority_orderer
    assert result.coalesce_policy is coalesce_policy
    assert result.conflict_resolver is conflict_resolver
    assert result.join_planner is join_planner
    mock_orderer_cls.assert_called_once_with(
        logger,
        column_groups=("priority",),
    )
    mock_coalesce_policy_cls.assert_called_once_with(logger, priority_orderer)
    assert mock_join_key_resolver_cls.call_args.kwargs["normalize_join_keys"] == {
        "doi",
        "pmid",
    }
    join_adapter_kwargs = mock_join_adapter_cls.call_args.kwargs
    assert join_adapter_kwargs["logger"] is logger
    assert join_adapter_kwargs["join_type_resolver"]() == "left"
    assert mock_dependency_joiner_cls.call_args.kwargs["join_executor"] is join_executor
    assert mock_join_planner_cls.call_args.kwargs["join_executor"] is join_executor
    assert (
        mock_join_planner_cls.call_args.kwargs["dependency_joiner"] is dependency_joiner
    )
