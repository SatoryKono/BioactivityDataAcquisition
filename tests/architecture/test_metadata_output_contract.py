"""Architecture tests for unified output metadata contract (ADR-029).

Verifies that all layer metadata classes follow the unified
output metadata pattern.
"""

from __future__ import annotations

import pytest

import types

from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    BronzeMetadata,
    BronzeOutputExt,
    GoldMetadata,
    GoldOutputExt,
    SilverMetadata,
    SilverOutputExt,
)


pytestmark = pytest.mark.architecture

def test_all_layer_metadata_have_base_output() -> None:
    """GIVEN layer metadata classes THEN all have BaseOutputMetadata output field."""
    for cls in [BronzeMetadata, SilverMetadata, GoldMetadata]:
        assert hasattr(cls, "model_fields"), f"{cls.__name__} is not a Pydantic model"
        assert "output" in cls.model_fields, f"{cls.__name__} missing 'output' field"

        field_info = cls.model_fields["output"]
        assert field_info.annotation == BaseOutputMetadata, (
            f"{cls.__name__}.output should be BaseOutputMetadata, got {field_info.annotation}"
        )


def test_all_layer_metadata_have_output_ext() -> None:
    """GIVEN layer metadata classes THEN all have layer-specific output_ext field."""
    expected = {
        BronzeMetadata: BronzeOutputExt,
        SilverMetadata: SilverOutputExt,
        GoldMetadata: GoldOutputExt,
    }

    for cls, ext_cls in expected.items():
        assert hasattr(cls, "model_fields"), f"{cls.__name__} is not a Pydantic model"
        assert "output_ext" in cls.model_fields, (
            f"{cls.__name__} missing 'output_ext' field"
        )

        field_info = cls.model_fields["output_ext"]
        annotation = field_info.annotation
        # Support Union types (e.g., GoldOutputExt | CompositeOutputExt)
        if isinstance(annotation, types.UnionType):
            assert ext_cls in annotation.__args__, (
                f"{cls.__name__}.output_ext should include {ext_cls.__name__}, got {annotation}"
            )
        else:
            assert annotation == ext_cls, (
                f"{cls.__name__}.output_ext should be {ext_cls.__name__}, got {annotation}"
            )


def test_base_output_metadata_has_required_fields() -> None:
    """GIVEN BaseOutputMetadata THEN has all required common fields."""
    required_fields = [
        "record_count",
        "total_bytes",
        "content_hash",
        "write_started_at",
        "write_completed_at",
    ]

    for field_name in required_fields:
        assert field_name in BaseOutputMetadata.model_fields, (
            f"BaseOutputMetadata missing field: {field_name}"
        )


def test_base_output_metadata_has_computed_duration() -> None:
    """GIVEN BaseOutputMetadata THEN has computed write_duration_ms property."""
    # Check for computed field
    computed_fields = BaseOutputMetadata.model_computed_fields
    assert "write_duration_ms" in computed_fields, (
        "BaseOutputMetadata missing computed field: write_duration_ms"
    )


def test_bronze_output_ext_has_required_fields() -> None:
    """GIVEN BronzeOutputExt THEN has required Bronze-specific fields."""
    required_fields = ["files", "format", "compression"]

    for field_name in required_fields:
        assert field_name in BronzeOutputExt.model_fields, (
            f"BronzeOutputExt missing field: {field_name}"
        )


def test_silver_output_ext_has_required_fields() -> None:
    """GIVEN SilverOutputExt THEN has required Silver-specific fields."""
    required_fields = ["delta_version_before", "delta_version_after"]

    for field_name in required_fields:
        assert field_name in SilverOutputExt.model_fields, (
            f"SilverOutputExt missing field: {field_name}"
        )


def test_gold_output_ext_has_required_fields() -> None:
    """GIVEN GoldOutputExt THEN has required Gold-specific fields."""
    required_fields = ["partition_count", "format"]

    for field_name in required_fields:
        assert field_name in GoldOutputExt.model_fields, (
            f"GoldOutputExt missing field: {field_name}"
        )


def test_metadata_version_reflects_adr029() -> None:
    """GIVEN layer metadata classes THEN version is 1.1 for ADR-029."""
    for cls in [BronzeMetadata, SilverMetadata, GoldMetadata]:
        field_info = cls.model_fields["version"]
        assert field_info.default == "1.1", (
            f"{cls.__name__}.version should default to '1.1' for ADR-029"
        )


def test_base_output_forbids_extra_fields() -> None:
    """GIVEN BaseOutputMetadata THEN extra fields are forbidden."""
    config = BaseOutputMetadata.model_config
    assert config.get("extra") == "forbid", (
        "BaseOutputMetadata should forbid extra fields"
    )
