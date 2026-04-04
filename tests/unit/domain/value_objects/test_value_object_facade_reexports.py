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
def test_publication_field_groups_facade_reexports_canonical_symbols() -> None:
    """publication_field_groups should remain the public entrypoint over split modules."""
    from bioetl.domain.value_objects._publication_field_group_config import (
        DEFAULT_FIELD_GROUP_CONFIG as CanonicalDefaultFieldGroupConfig,
    )
    from bioetl.domain.value_objects._publication_field_group_config import (
        FieldGroupConfig as CanonicalFieldGroupConfig,
    )
    from bioetl.domain.value_objects._publication_field_group_types import (
        FIELD_TO_GROUP_MAPPING as CanonicalFieldToGroupMapping,
    )
    from bioetl.domain.value_objects._publication_field_group_types import (
        PublicationFieldGroup as CanonicalPublicationFieldGroup,
    )
    from bioetl.domain.value_objects.publication_field_groups import (
        DEFAULT_FIELD_GROUP_CONFIG,
        FIELD_TO_GROUP_MAPPING,
        FieldGroupConfig,
        PublicationFieldGroup,
    )

    assert DEFAULT_FIELD_GROUP_CONFIG is CanonicalDefaultFieldGroupConfig
    assert FIELD_TO_GROUP_MAPPING is CanonicalFieldToGroupMapping
    assert FieldGroupConfig is CanonicalFieldGroupConfig
    assert PublicationFieldGroup is CanonicalPublicationFieldGroup
