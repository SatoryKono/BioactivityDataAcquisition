"""Unit tests for CompositeSupportServicesFactory merge wiring."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
    CompositeSupportServicesFactory,
)
from bioetl.application.composite.join_planner_helpers import (
    resolve_field_aliases_from_registry,
)
from bioetl.domain.composite.strategy import MergeStrategy


def _make_factory() -> CompositeSupportServicesFactory:
    config = SimpleNamespace(
        name="composite_publication",
        merge=SimpleNamespace(strategy=MergeStrategy.LEFT_OUTER),
        cross_validation=SimpleNamespace(enabled=False),
        dq=SimpleNamespace(),
        execution=SimpleNamespace(max_concurrency=3),
    )
    runtime = SimpleNamespace(resume=False)
    settings = SimpleNamespace(data_dir="data")
    logger = MagicMock()
    storage = MagicMock()

    return CompositeSupportServicesFactory(
        config=config,
        runtime=runtime,
        settings=settings,
        logger=logger,
        storage=storage,
        run_id="run-123",
        resolve_gold_schema=lambda _name: None,
        load_field_group_registry=lambda _name, _logger: None,
        create_dq_report_service=lambda _logger, _settings: MagicMock(),
    )


@pytest.mark.unit
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_services_factory.MergeService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_services_factory.JoinPlannerService"
)
@patch(
    "bioetl.composition.bootstrap.runtime.composite_support_services_factory.DependencyJoinerService"
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
    assert join_planner_kwargs["field_alias_resolver"] is resolve_field_aliases_from_registry
    assert join_planner_kwargs["dependency_joiner"] is dependency_joiner
