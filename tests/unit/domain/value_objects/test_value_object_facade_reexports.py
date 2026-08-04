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
"""Unit tests for domain value-object public facade re-exports."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_value_objects_facade_resolves_exports_lazily() -> None:
    """Facade should not eagerly import every value-object symbol on package import."""
    import importlib
    import sys

    # Other domain tests may have already resolved the lazy attribute on the
    # shared package module. Re-import a clean facade so this test remains
    # order-independent, including under mutmut's clean-test collection.
    sys.modules.pop("bioetl.domain.value_objects", None)
    facade = importlib.import_module("bioetl.domain.value_objects")
    from bioetl.domain.value_objects.base import ValueObject as CanonicalValueObject

    assert "ValueObject" not in facade.__dict__

    assert facade.ValueObject is CanonicalValueObject
    assert "ValueObject" in facade.__dict__


@pytest.mark.unit
def test_removed_publication_field_groups_facade_stays_absent() -> None:
    """Removed publication field-group facade must stay absent."""
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bioetl.domain.value_objects.publication_field_groups")
