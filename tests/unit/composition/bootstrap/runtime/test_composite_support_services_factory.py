"""Unit tests for CompositeSupportServicesFactory merge wiring."""

from __future__ import annotations

from typing import Any, cast
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointService
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
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
    checkpoint_manager_cls: type[CompositeCheckpointService] = CompositeCheckpointService,
) -> CompositeSupportServicesFactory:
    config = cast(
        Any,
        SimpleNamespace(
            name="composite_publication",
            merge=SimpleNamespace(strategy=MergeStrategy.LEFT_OUTER),
            cross_validation=SimpleNamespace(enabled=False),
            dq=SimpleNamespace(),
            execution=SimpleNamespace(max_concurrency=3),
        ),
    )
    runtime = CompositeRuntimeConfig(resume=False)
    settings = cast(Any, SimpleNamespace(data_dir="data"))
    logger = MagicMock()
    storage = MagicMock()

    infra_context = cast(Any, CompositeInfrastructureContext)(
        run_id="run-123",
        settings=settings,
        logger=logger,
        storage=storage,
        lock=MagicMock(),
    )

    return CompositeSupportServicesFactory(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        resolve_gold_schema=lambda _name: None,
        load_field_group_registry=lambda _name, _logger: None,
        create_dq_report_service=lambda _logger, _settings: MagicMock(),
        checkpoint_manager_cls=checkpoint_manager_cls,
    )


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_services_factory.MergeService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_service_builders.JoinPlannerService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_service_builders.DependencyJoinerService"
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

    result = factory._create_merge_service(
        delta_reader=MagicMock(),
        field_group_registry=None,
        cross_validator=None,
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
    "bioetl.composition.bootstrap.runtime.composite_support_service_builders.FSMStateHelperService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_service_builders.EnrichmentCoordinatorService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_service_builders.DependencyCoordinatorService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_service_builders.KeyExtractorService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_service_builders.bootstrap_composite_checkpoint_port"
)
def test_build_uses_canonical_composite_checkpoint_port(
    mock_bootstrap_checkpoint_port: MagicMock,
    mock_key_extractor_cls: MagicMock,
    mock_dependency_coordinator_cls: MagicMock,
    mock_enrichment_coordinator_cls: MagicMock,
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

    mock_bootstrap_checkpoint_port.return_value = checkpoint_storage
    mock_key_extractor_cls.return_value = MagicMock(name="key_extractor")
    mock_dependency_coordinator_cls.return_value = MagicMock(
        name="dependency_coordinator"
    )
    mock_enrichment_coordinator_cls.return_value = MagicMock(name="coordinator")
    mock_fsm_state_helper_cls.return_value = MagicMock(name="fsm_state_helper")
    factory._create_delta_reader = MagicMock(
        return_value=MagicMock(name="delta_reader")
    )
    factory._create_cross_validator = MagicMock(return_value=None)
    factory._create_merge_service = MagicMock(return_value=merger)

    result = factory.build()

    assert result.checkpoint_manager is checkpoint_manager
    mock_bootstrap_checkpoint_port.assert_called_once_with()
    cast(MagicMock, checkpoint_manager_cls).assert_called_once_with(
        composite_name="composite_publication",
        run_id="run-123",
        storage=checkpoint_storage,
        logger=factory._infra.logger,
        resume=False,
    )
