"""Unit tests for the composite validation composition factory."""

from __future__ import annotations

from bioetl.composition.factories.dq import create_composite_validation_service
from bioetl.domain.services.aggregation_validator import AggregationValidator
from bioetl.domain.services.composite_validation_layer import CompositeValidator
from bioetl.domain.services.cross_validation_validator import CrossValidationValidator
from bioetl.domain.services.preflight_governance import PreflightGovernor


def test_create_composite_validation_service_returns_default_wiring() -> None:
    """Factory should assemble the default composite validation collaborators."""
    service = create_composite_validation_service()

    assert isinstance(service, CompositeValidator)
    assert isinstance(service._aggregation_validator, AggregationValidator)
    assert isinstance(service._cross_validation_validator, CrossValidationValidator)
    assert isinstance(service._preflight_governance, PreflightGovernor)


def test_factory_returns_fresh_service_instances() -> None:
    """Factory should return independent service instances."""
    first = create_composite_validation_service()
    second = create_composite_validation_service()

    assert first is not second
