"""Composition factory for composite validation services."""

from __future__ import annotations

from bioetl.domain.services.aggregation_validator import AggregationValidator
from bioetl.domain.services.composite_validation_layer import CompositeValidator
from bioetl.domain.services.cross_validation_validator import CrossValidationValidator
from bioetl.domain.services.preflight_governance import PreflightGovernor


def create_composite_validation_service() -> CompositeValidator:
    """Create the default composite validation service wiring."""
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )
