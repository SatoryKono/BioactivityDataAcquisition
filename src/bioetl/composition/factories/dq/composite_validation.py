"""Composition factory for composite validation services."""

from __future__ import annotations

from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_validation_layer import CompositeValidator
from bioetl.domain.behavior.cross_validation_validator import CrossValidationValidator
from bioetl.domain.behavior.preflight_governance import PreflightGovernor


def create_composite_validation_service() -> CompositeValidator:
    """Create the default composite validation service wiring."""
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )
