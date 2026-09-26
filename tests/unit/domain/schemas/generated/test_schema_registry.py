# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Same-path owner tests for generated schema registry module."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from bioetl.domain.schemas.generated.registry import (
    CANONICAL_SCHEMA_REGISTRY,
    CanonicalSchemaRegistryEntry,
)


pytestmark = pytest.mark.unit


def test_generated_registry_exposes_entries_for_canonical_schema_inventory() -> None:
    assert CANONICAL_SCHEMA_REGISTRY
    assert all(
        isinstance(entry, CanonicalSchemaRegistryEntry)
        for entry in CANONICAL_SCHEMA_REGISTRY
    )
    assert any(
        entry.provider == "pubchem" and entry.entity == "compound"
        for entry in CANONICAL_SCHEMA_REGISTRY
    )


def test_generated_registry_entry_dataclass_is_frozen() -> None:
    entry = CANONICAL_SCHEMA_REGISTRY[0]
    with pytest.raises(FrozenInstanceError):
        entry.provider = "mutated"  # type: ignore[misc]
