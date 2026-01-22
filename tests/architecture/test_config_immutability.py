"""Tests for configuration immutability.

Verifies that domain configuration objects are immutable (frozen) and that
collection fields are converted to tuples to prevent accidental modification.
"""

from dataclasses import FrozenInstanceError
import pytest
from bioetl.domain.config import (
    DQConfig,
    PipelineConfig,
    RuntimeConfig,
    TableConfig,
    ValidationConfig,
)
from bioetl.domain.types import RunType


def test_validation_config_immutability():
    """Verify ValidationConfig is immutable."""
    config = ValidationConfig()

    with pytest.raises(FrozenInstanceError):
        config.min_publication_year = 2000


def test_dq_config_immutability():
    """Verify DQConfig and its collection fields are immutable."""
    config = DQConfig(
        field_validations=[],
        cross_field_validations=[],
        conditional_validations=[]
    )

    # Test top-level immutability
    with pytest.raises(FrozenInstanceError):
        config.soft_fail_threshold = 0.5

    # Test collection conversion to tuple
    assert isinstance(config.field_validations, tuple)
    assert isinstance(config.cross_field_validations, tuple)
    assert isinstance(config.conditional_validations, tuple)


def test_table_config_immutability():
    """Verify TableConfig and its collection fields are immutable."""
    config = TableConfig(
        primary_keys=["id"],
        partition_cols=["year"]
    )

    # Test top-level immutability
    with pytest.raises(FrozenInstanceError):
        config.silver_table = "new_table"

    # Test collection conversion to tuple
    assert isinstance(config.primary_keys, tuple)
    assert isinstance(config.partition_cols, tuple)


def test_pipeline_config_immutability():
    """Verify PipelineConfig and its collection fields are immutable."""
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        primary_keys=["id"],
        silver_table="silver.test",
        fields=["col1", "col2"],
        transform_steps=["step1", "step2"]
    )

    # Test top-level immutability
    with pytest.raises(FrozenInstanceError):
        config.batch_size = 500

    # Test collection conversion to tuple
    assert isinstance(config.primary_keys, tuple)
    assert isinstance(config.fields, tuple)
    assert isinstance(config.transform_steps, tuple)


def test_runtime_config_immutability():
    """Verify RuntimeConfig is immutable."""
    config = RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        limit=100
    )

    with pytest.raises(FrozenInstanceError):
        config.resume = True
