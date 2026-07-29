# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for the composite validation composition factory."""

from __future__ import annotations

import pytest

from bioetl.composition.factories.dq import create_composite_validation_service
from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_validation_layer import CompositeValidator
from bioetl.domain.behavior.cross_validation_validator import CrossValidationValidator
from bioetl.domain.behavior.preflight_governance import PreflightGovernor


pytestmark = pytest.mark.unit


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
