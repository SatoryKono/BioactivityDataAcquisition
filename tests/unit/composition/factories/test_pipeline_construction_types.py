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
"""Unit tests for pipeline-construction protocol contracts."""

from __future__ import annotations

import pytest

from typing import Protocol
from typing import get_type_hints

from bioetl.composition.factories.pipeline import construction_types
from bioetl.composition.factories.pipeline.entity_type_extractor import (
    EntityTypeExtractor,
)


pytestmark = pytest.mark.unit


def test_pipeline_construction_protocols_expose_expected_public_contracts() -> None:
    """Construction protocol module should expose stable callable contracts."""
    assert issubclass(EntityTypeExtractor, Protocol)
    assert issubclass(construction_types.DomainConfigMapper, Protocol)
    assert issubclass(construction_types.ContractPolicyLoaderProtocol, Protocol)
    assert issubclass(construction_types._SchemaBuilder, Protocol)


def test_pipeline_construction_protocols_preserve_expected_return_hints() -> None:
    """Construction protocol call signatures should keep their typed return contracts."""
    entity_hints = get_type_hints(EntityTypeExtractor.__call__)
    schema_hints = get_type_hints(construction_types._SchemaBuilder.to_schema)

    assert entity_hints["return"] == str | None
    assert schema_hints["return"] is object
