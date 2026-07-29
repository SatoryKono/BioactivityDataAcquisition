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
"""Unit tests for domain value-object public facade re-exports."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_value_objects_facade_resolves_exports_lazily() -> None:
    """Facade should not eagerly import every value-object symbol on package import."""
    import bioetl.domain.value_objects as facade
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
