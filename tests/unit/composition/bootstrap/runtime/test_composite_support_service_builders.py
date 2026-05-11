"""Unit tests for composite support service builder functions."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.composite.runtime_wiring_api import (
    CompositeCheckpointServiceContext,
)
from bioetl.application.composite.join_key_normalization import (
    JOIN_KEY_NORMALIZATION_POLICIES,
)
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
    include_to_dict: bool = True,
) -> Any:
    config = SimpleNamespace(
        name="composite_publication",
        version="1.0.0",
        enrichers=(),
        dependencies=(),
        dq=SimpleNamespace(),
        execution=SimpleNamespace(max_concurrency=3),
        cross_validation=SimpleNamespace(enabled=quarantine_enabled),
        merge=SimpleNamespace(
            strategy=MergeStrategy.LEFT_OUTER,
            column_groups=column_groups,
        ),
    )
    if include_to_dict:
        config.to_dict = lambda: {
            "name": "composite_publication",
            "version": "1.0.0",
            "enrichers": [],
            "dependencies": [],
            "merge": {"strategy": "left_outer"},
        }
    return cast(
        Any,
        config,
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
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
    )
    mock_seed_key_resolver.assert_called_once_with(
        logger,
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
    )
    mock_chained_key_resolver.assert_called_once_with(
        logger,
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
    )
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
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_quarantine_adapter"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_composite_checkpoint_writer"
)
def test_build_runtime_management_services_enables_quarantine_when_configured(
    mock_checkpoint_port: MagicMock,
    mock_quarantine_port: MagicMock,
    mock_fsm_state_helper_cls: MagicMock,
) -> None:
    infra_context = cast(
        Any, SimpleNamespace(metrics=MagicMock(name="metrics"), clock=None)
    )
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
    checkpoint_manager_cls.assert_called_once()
    checkpoint_context = checkpoint_manager_cls.call_args.args[0]
    assert isinstance(checkpoint_context, CompositeCheckpointServiceContext)
    assert checkpoint_context.composite_name == "composite_publication"
    assert checkpoint_context.run_id == "run-123"
    assert checkpoint_context.storage is checkpoint_storage
    assert checkpoint_context.logger is logger
    assert checkpoint_context.resume is True
    assert isinstance(checkpoint_context.expected_effective_config_hash, str)
    assert len(checkpoint_context.expected_effective_config_hash) == 64
    assert checkpoint_context.expected_contract_ref == "composite_publication"
    assert checkpoint_context.expected_contract_version == "1.0.0"
    assert checkpoint_context.expected_manifest_id is None
    assert checkpoint_context.expected_execution_fingerprint is None
    assert checkpoint_context.expected_dq_contract_compatibility_hash is None
    assert checkpoint_context.expected_effective_config_artifact_id is None
    assert checkpoint_context.expected_input_snapshot_fingerprint is None
    assert checkpoint_context.run_ledger_port is None
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
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_quarantine_adapter"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_composite_checkpoint_writer"
)
def test_build_runtime_management_services_skips_quarantine_when_disabled(
    mock_checkpoint_port: MagicMock,
    mock_quarantine_port: MagicMock,
    mock_fsm_state_helper_cls: MagicMock,
) -> None:
    infra_context = cast(
        Any, SimpleNamespace(metrics=MagicMock(name="metrics"), clock=None)
    )
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
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_quarantine_adapter"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_composite_checkpoint_writer"
)
def test_build_runtime_management_services_propagates_config_hash_when_available(
    mock_checkpoint_port: MagicMock,
    mock_quarantine_port: MagicMock,
    mock_fsm_state_helper_cls: MagicMock,
) -> None:
    infra_context = cast(
        Any, SimpleNamespace(metrics=MagicMock(name="metrics"), clock=None)
    )
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

    checkpoint_context = checkpoint_manager_cls.call_args.args[0]
    assert isinstance(checkpoint_context, CompositeCheckpointServiceContext)
    config_hash = checkpoint_context.expected_effective_config_hash
    assert isinstance(config_hash, str)
    assert len(config_hash) == 64


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.FSMStateHelperService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_quarantine_adapter"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_composite_checkpoint_writer"
)
def test_build_runtime_management_services_prefers_control_plane_effective_hash(
    mock_checkpoint_port: MagicMock,
    mock_quarantine_port: MagicMock,
    mock_fsm_state_helper_cls: MagicMock,
) -> None:
    infra_context = cast(
        Any, SimpleNamespace(metrics=MagicMock(name="metrics"), clock=None)
    )
    logger = MagicMock()
    settings = MagicMock()
    runtime = cast(Any, SimpleNamespace(resume=False))
    checkpoint_manager_cls = cast(Any, MagicMock(return_value=MagicMock()))

    mock_checkpoint_port.return_value = MagicMock(name="checkpoint_storage")
    mock_quarantine_port.return_value = MagicMock(name="quarantine_port")
    mock_fsm_state_helper_cls.return_value = MagicMock(name="fsm_state_helper")

    build_runtime_management_services(
        config=_make_config(quarantine_enabled=False),
        runtime=runtime,
        infra_context=infra_context,
        settings=settings,
        logger=logger,
        run_id="run-123",
        checkpoint_manager_cls=checkpoint_manager_cls,
        create_dq_report_service=MagicMock(return_value=MagicMock()),
        control_plane_bundle=SimpleNamespace(
            manifest_id="manifest-123",
            execution_fingerprint="fingerprint-123",
            dq_contract_compatibility_hash="dq-123",
            effective_config_artifact_id="artifact-123",
            effective_config_hash="f" * 64,
            input_snapshot_fingerprint="snapshot-fp-123",
            run_ledger_service=None,
        ),
    )

    checkpoint_context = checkpoint_manager_cls.call_args.args[0]
    assert isinstance(checkpoint_context, CompositeCheckpointServiceContext)
    assert checkpoint_context.expected_effective_config_hash == ("f" * 64)
    assert checkpoint_context.expected_input_snapshot_fingerprint == "snapshot-fp-123"


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.FSMStateHelperService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_quarantine_adapter"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.bootstrap_composite_checkpoint_writer"
)
def test_build_runtime_management_services_fails_when_effective_hash_cannot_be_resolved(
    mock_checkpoint_port: MagicMock,
    mock_quarantine_port: MagicMock,
    mock_fsm_state_helper_cls: MagicMock,
) -> None:
    infra_context = cast(
        Any, SimpleNamespace(metrics=MagicMock(name="metrics"), clock=None)
    )
    mock_checkpoint_port.return_value = MagicMock(name="checkpoint_storage")
    mock_quarantine_port.return_value = MagicMock(name="quarantine_port")
    mock_fsm_state_helper_cls.return_value = MagicMock(name="fsm_state_helper")

    with pytest.raises(
        ValueError,
        match="expected_effective_config_hash",
    ):
        build_runtime_management_services(
            config=_make_config(quarantine_enabled=False, include_to_dict=False),
            runtime=cast(Any, SimpleNamespace(resume=False)),
            infra_context=infra_context,
            settings=MagicMock(),
            logger=MagicMock(),
            run_id="run-123",
            checkpoint_manager_cls=cast(Any, MagicMock(return_value=MagicMock())),
            create_dq_report_service=MagicMock(return_value=MagicMock()),
        )


@pytest.mark.unit
def test_build_merge_dependencies_creates_required_services() -> None:
    """Test that build_merge_dependencies creates all required services without errors."""
    from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
        MergeDependenciesBundle,
    )

    logger = MagicMock()

    # Test that the function runs without errors and returns a valid bundle
    result = build_merge_dependencies(
        config=_make_config(column_groups=("priority",)),
        logger=logger,
        resolve_join_how=lambda strategy: (
            "left" if strategy is MergeStrategy.LEFT_OUTER else "inner"
        ),
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
        system_columns_to_drop=frozenset({"_run_id"}),
    )

    # Verify that all required services are created and have the expected types
    assert isinstance(result, MergeDependenciesBundle)
    assert hasattr(result, "deduplicator")
    assert hasattr(result, "aggregator")
    assert hasattr(result, "renamer")
    assert hasattr(result, "orderer")
    assert hasattr(result, "priority_orderer")
    assert hasattr(result, "coalesce_policy")
    assert hasattr(result, "conflict_resolver")
    assert hasattr(result, "join_planner")
    assert hasattr(result, "order_service")

    # Verify that services are properly initialized (not None)
    assert result.deduplicator is not None
    assert result.aggregator is not None
    assert result.renamer is not None
    assert result.orderer is not None
    assert result.priority_orderer is None
    assert result.coalesce_policy is not None
    assert result.conflict_resolver is not None
    assert result.join_planner is not None
    assert result.order_service is not None
    assert result.orderer is result.order_service
