"""Unit tests for CompositeSupportServicesFactory merge wiring."""

from __future__ import annotations

from typing import Any, cast
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointService
from bioetl.application.composite.runtime_wiring_api import (
    CompositeCheckpointServiceContext,
    JoinHow,
)
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite_merge_service_builder import (
    _resolve_join_how,
    build_composite_merge_service,
)
from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
    CompositeSupportServicesFactory,
)
from bioetl.composition.bootstrap.runtime.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.application.composite.join_planner_helpers import (
    resolve_field_aliases_from_registry,
)
from bioetl.domain.composite.strategy import MergeStrategy


def _make_factory(
    *,
    checkpoint_manager_cls: type[
        CompositeCheckpointService
    ] = CompositeCheckpointService,
) -> CompositeSupportServicesFactory:
    config = cast(
        Any,
        SimpleNamespace(
            name="composite_publication",
            version="1.0.0",
            enrichers=(),
            dependencies=(),
            merge=SimpleNamespace(strategy=MergeStrategy.LEFT_OUTER),
            cross_validation=SimpleNamespace(enabled=False),
            dq=SimpleNamespace(),
            execution=SimpleNamespace(max_concurrency=3),
            to_dict=lambda: {
                "name": "composite_publication",
                "version": "1.0.0",
                "enrichers": [],
                "dependencies": [],
                "merge": {"strategy": "left_outer"},
            },
        ),
    )
    runtime = CompositeRuntimeConfig(resume=False)
    settings = cast(Any, SimpleNamespace(data_dir="data"))
    logger = MagicMock()
    metrics = MagicMock()
    storage = MagicMock()

    infra_context = cast(Any, CompositeInfrastructureContext)(
        run_id="run-123",
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracer=MagicMock(),
        storage=storage,
        lock=MagicMock(),
    )

    return CompositeSupportServicesFactory(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        resolve_gold_schema=lambda _name: None,
        load_field_group_registry=lambda _name, _logger: None,
        create_dq_report_service=lambda _logger, _settings, _metrics: MagicMock(),
        checkpoint_manager_cls=checkpoint_manager_cls,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("strategy", "expected"),
    [
        (MergeStrategy.LEFT_OUTER, "left"),
        (MergeStrategy.INNER, "inner"),
        (MergeStrategy.UNION, "full"),
    ],
)
def test_resolve_join_how_maps_supported_merge_strategies(
    strategy: MergeStrategy,
    expected: JoinHow,
) -> None:
    assert _resolve_join_how(strategy) == expected


@pytest.mark.unit
def test_resolve_join_how_defaults_unknown_strategy_to_left_join() -> None:
    assert _resolve_join_how(cast(MergeStrategy, object())) == "left"


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_service_builder.MergeService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.JoinPlannerService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder.DependencyJoinerService"
)
def test_create_merge_service_wires_join_planner_field_alias_resolver(
    mock_dependency_joiner_cls: MagicMock,
    mock_join_planner_cls: MagicMock,
    mock_merge_service_cls: MagicMock,
) -> None:
    factory = _make_factory()
    dependency_joiner = MagicMock(name="dependency_joiner")
    merge_service = MagicMock(name="merge_service")
    mock_dependency_joiner_cls.return_value = dependency_joiner
    mock_join_planner_cls.return_value = MagicMock(name="join_planner")
    mock_merge_service_cls.return_value = merge_service

    result = build_composite_merge_service(
        config=factory._config,
        storage=factory._infra.storage,
        resolve_gold_schema=factory._resolve_gold_schema,
        delta_reader=MagicMock(),
        field_group_registry=None,
        cross_validator=None,
        logger=factory._infra.logger,
        system_columns_to_drop=factory._SYSTEM_COLUMNS_TO_DROP,
        normalization_policies=factory._JOIN_KEY_NORMALIZATION_POLICIES,
    )

    assert result is merge_service
    dependency_joiner_kwargs = mock_dependency_joiner_cls.call_args.kwargs
    assert (
        dependency_joiner_kwargs["field_alias_resolver"]
        is resolve_field_aliases_from_registry
    )
    join_planner_kwargs = mock_join_planner_cls.call_args.kwargs
    assert (
        join_planner_kwargs["field_alias_resolver"]
        is resolve_field_aliases_from_registry
    )
    assert join_planner_kwargs["dependency_joiner"] is dependency_joiner


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.FSMStateHelperService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_runtime_context.build_composite_control_plane_bundle"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.EnrichmentCoordinatorService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.DependencyCoordinatorService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_execution_support_builder.KeyExtractorService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_composite_checkpoint_writer"
)
def test_build_uses_canonical_composite_checkpoint_port(
    mock_bootstrap_checkpoint_adapter: MagicMock,
    mock_key_extractor_cls: MagicMock,
    mock_dependency_coordinator_cls: MagicMock,
    mock_enrichment_coordinator_cls: MagicMock,
    mock_build_control_plane_bundle: MagicMock,
    mock_fsm_state_helper_cls: MagicMock,
) -> None:
    checkpoint_manager = MagicMock(name="checkpoint_manager")
    checkpoint_manager_cls = cast(
        Any,
        MagicMock(return_value=checkpoint_manager),
    )
    factory = _make_factory(checkpoint_manager_cls=checkpoint_manager_cls)
    checkpoint_storage = MagicMock(name="checkpoint_storage")
    merger = MagicMock(name="merger")

    mock_bootstrap_checkpoint_adapter.return_value = checkpoint_storage
    mock_build_control_plane_bundle.return_value = SimpleNamespace(
        manifest_id="manifest-123",
        execution_fingerprint="fingerprint-123",
        run_ledger_service=MagicMock(name="run_ledger_service"),
        config_hash="hash-123",
        effective_config_hash="e" * 64,
        dq_contract_compatibility_hash="dq-hash-123",
        effective_config_artifact_id="artifact-123",
        input_snapshot_fingerprint="snapshot-fingerprint-123",
        contract_ref="composite_publication",
        contract_version="1.0.0",
    )
    mock_key_extractor_cls.return_value = MagicMock(name="key_extractor")
    mock_dependency_coordinator_cls.return_value = MagicMock(
        name="dependency_coordinator"
    )
    mock_enrichment_coordinator_cls.return_value = MagicMock(name="coordinator")
    mock_fsm_state_helper_cls.return_value = MagicMock(name="fsm_state_helper")
    with patch(
        "bioetl.composition.bootstrap.runtime.composite_support_services_factory.build_composite_merge_service",
        return_value=merger,
    ) as mock_build_merge_service:
        result = factory.build()

    assert result.checkpoint_manager is checkpoint_manager
    mock_bootstrap_checkpoint_adapter.assert_called_once_with()
    factory._infra.logger.bind.assert_called_once_with(manifest_id="manifest-123")
    mock_build_merge_service.assert_called_once()
    checkpoint_manager_cls.assert_called_once()
    checkpoint_context = checkpoint_manager_cls.call_args.args[0]
    assert isinstance(checkpoint_context, CompositeCheckpointServiceContext)
    assert checkpoint_context.composite_name == "composite_publication"
    assert checkpoint_context.run_id == "run-123"
    assert checkpoint_context.storage is checkpoint_storage
    assert checkpoint_context.logger is factory._infra.logger.bind.return_value
    assert checkpoint_context.resume is False
    assert isinstance(checkpoint_context.expected_effective_config_hash, str)
    assert len(checkpoint_context.expected_effective_config_hash) == 64
    assert checkpoint_context.expected_contract_ref == "composite_publication"
    assert checkpoint_context.expected_contract_version == "1.0.0"
    assert checkpoint_context.expected_manifest_id == "manifest-123"
    assert checkpoint_context.expected_execution_fingerprint == "fingerprint-123"
    assert checkpoint_context.expected_dq_contract_compatibility_hash == "dq-hash-123"
    assert checkpoint_context.expected_effective_config_artifact_id == "artifact-123"
    assert (
        checkpoint_context.expected_input_snapshot_fingerprint
        == "snapshot-fingerprint-123"
    )
    assert checkpoint_context.run_ledger_port is (
        mock_build_control_plane_bundle.return_value.run_ledger_service.ledger_port
    )
    assert checkpoint_context.metrics is factory._infra.metrics
    assert result.manifest_id == "manifest-123"
    assert (
        result.run_ledger_service
        is mock_build_control_plane_bundle.return_value.run_ledger_service
    )
