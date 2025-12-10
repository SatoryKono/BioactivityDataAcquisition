"""Tests for transform services (hash, timestamp, index)."""

import re
from datetime import datetime, timezone

import pandas as pd

from bioetl.infrastructure.transform.factories import (
    default_hash_service,
    default_index_generator,
    default_timestamp_provider,
)
from bioetl.domain.transform.transformers import (
    IndexColumnTransformerImpl,
    DatabaseVersionTransformerImpl,
    FulldateTransformerImpl,
)


def test_hash_service_add_hash_columns():
    """Test that hash service adds hash columns correctly."""
    svc = default_hash_service()
    src = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    out = svc.add_hash_columns(src, business_key_cols=["a"])

    assert "hash_row" in out.columns
    assert "hash_business_key" in out.columns
    assert "a" not in src.columns or "hash_row" not in src.columns  # immutability


def test_hash_service_hash_row():
    """Test hash_row computes deterministic hash."""
    svc = default_hash_service()
    row = {"a": 1, "b": "test"}

    hash1 = svc.hash_row(row)
    hash2 = svc.hash_row(row)

    assert hash1 == hash2
    assert len(hash1) == 64  # blake2b-256 hex


def test_hash_service_hash_business_key():
    """Test hash_business_key computes hash for specific columns."""
    svc = default_hash_service()
    row = {"a": 1, "b": "test", "c": 3}

    hash1 = svc.hash_business_key(row, ["a", "b"])
    hash2 = svc.hash_business_key(row, ["a", "b"])

    assert hash1 == hash2
    assert len(hash1) == 64


def test_index_generator_sequential():
    """Test sequential index generation."""
    gen = default_index_generator()

    assert gen.next_index() == 0
    assert gen.next_index() == 1
    assert gen.next_index() == 2

    gen.reset()
    assert gen.next_index() == 0


def test_index_generator_with_start():
    """Test index generator with custom start."""
    gen = default_index_generator(start=100)

    assert gen.next_index() == 100
    assert gen.next_index() == 101


def test_index_column_transformer():
    """Test IndexColumnTransformerImpl adds index column."""
    gen = default_index_generator()
    transformer = IndexColumnTransformerImpl(index_generator=gen)
    src = pd.DataFrame({"a": [1, 2, 3]})

    out = transformer.apply(src)

    assert "index" in out.columns
    assert list(out["index"]) == [0, 1, 2]
    assert "index" not in src.columns  # immutability


def test_timestamp_provider_deterministic():
    """Test deterministic timestamp provider."""
    fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    provider = default_timestamp_provider(fixed_time=fixed_time)

    ts1 = provider.get_extraction_timestamp()
    ts2 = provider.get_extraction_timestamp()

    assert ts1 == ts2 == fixed_time


def test_timestamp_provider_uses_current_time():
    """Test timestamp provider uses current time if not fixed."""
    provider = default_timestamp_provider()

    ts = provider.get_extraction_timestamp()

    assert ts.tzinfo is not None
    assert (datetime.now(timezone.utc) - ts).total_seconds() < 1


def test_fulldate_transformer():
    """Test FulldateTransformerImpl adds extracted_at column."""
    fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    provider = default_timestamp_provider(fixed_time=fixed_time)
    transformer = FulldateTransformerImpl(timestamp_provider=provider)
    src = pd.DataFrame({"a": [1, 2, 3]})

    out = transformer.apply(src)

    assert "extracted_at" in out.columns
    vals = out["extracted_at"].unique()
    assert len(vals) == 1
    ts = vals[0]
    assert isinstance(ts, str) and "T" in ts
    assert re.search(r"\d{4}-\d{2}-\d{2}T", ts)


def test_database_version_transformer():
    """Test DatabaseVersionTransformerImpl adds version column."""
    transformer = DatabaseVersionTransformerImpl(
        database_version_provider=lambda: "v1.2.3"
    )
    src = pd.DataFrame({"a": [1]})

    out = transformer.apply(src)

    assert "database_version" in out.columns
    assert all(out["database_version"] == "v1.2.3")


def test_database_version_transformer_empty_df():
    """Test version transformer handles empty DataFrame."""
    transformer = DatabaseVersionTransformerImpl(
        database_version_provider=lambda: "v1.2.3"
    )
    src = pd.DataFrame({"a": []})

    out = transformer.apply(src)

    assert "database_version" in out.columns
    assert out["database_version"].dtype == object or out["database_version"].empty


def test_database_version_transformer_none_version():
    """Test version transformer skips when version is None."""
    transformer = DatabaseVersionTransformerImpl(
        database_version_provider=lambda: None
    )
    src = pd.DataFrame({"a": [1]})

    out = transformer.apply(src)

    assert "database_version" not in out.columns
