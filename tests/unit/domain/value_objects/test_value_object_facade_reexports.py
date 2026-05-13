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
def test_activity_values_facade_reexports_canonical_symbols() -> None:
    """activity_values should remain the public entrypoint over split modules."""
    from bioetl.domain.value_objects.activity_concentration import (
        Concentration as CanonicalConcentration,
    )
    from bioetl.domain.value_objects.activity_concentration import (
        ConcentrationUnit as CanonicalConcentrationUnit,
    )
    from bioetl.domain.value_objects.activity_type import (
        ActivityType as CanonicalActivityType,
    )
    from bioetl.domain.value_objects.activity_values import (
        ActivityType,
        Concentration,
        ConcentrationUnit,
        PChemblValue,
    )
    from bioetl.domain.value_objects.pchembl_value import (
        PChemblValue as CanonicalPChemblValue,
    )

    assert ActivityType is CanonicalActivityType
    assert Concentration is CanonicalConcentration
    assert ConcentrationUnit is CanonicalConcentrationUnit
    assert PChemblValue is CanonicalPChemblValue


@pytest.mark.unit
def test_removed_publication_field_groups_facade_stays_absent() -> None:
    """Removed publication field-group facade must stay absent."""
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bioetl.domain.value_objects.publication_field_groups")
