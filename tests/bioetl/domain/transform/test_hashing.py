import json
from pathlib import Path

import pandas as pd
import pytest

from bioetl.infrastructure.transform.impl.hasher import (
    HasherImpl,
    _serialize_canonical,
    blake2b_hash_hex,
)


def canonical_json_from_record(data):
    """Helper to access internal serialization for testing."""
    return _serialize_canonical(data)


def test_canonical_json_sorting():
    """Test that keys are sorted recursively."""
    data = {"b": 1, "a": 2, "c": {"y": 3, "x": 4}}
    canonical = canonical_json_from_record(data)
    # Expected: {"a":2,"b":1,"c":{"x":4,"y":3}}
    expected = '{"a":2,"b":1,"c":{"x":4,"y":3}}'
    assert canonical == expected


def test_canonical_json_floats():
    """Test float formatting %.15g."""
    # 1/3 approx 0.333333333333333
    val = 1.0 / 3.0
    data = {"val": val}
    canonical = canonical_json_from_record(data)
    # Check that it contains the formatted float.
    # "%.15g" % (1/3) -> '0.333333333333333'
    assert "0.333333333333333" in canonical

    # Integer as float should be formatted as integer-looking if no decimal needed?
    # %.15g for 2.0 is '2'
    assert canonical_json_from_record({"v": 2.0}) == '{"v":2}'

    # Small numbers
    assert canonical_json_from_record({"v": 1e-20}) == '{"v":1e-20}'


def test_canonical_json_unicode_nfc():
    """Test Unicode normalization to NFC."""
    # 'café' can be written as 'cafe' + combining acute accent
    decomposed = "cafe\u0301"
    composed = "caf\u00e9"

    # They should serialize to the same NFC JSON string
    json1 = canonical_json_from_record({"t": decomposed})
    json2 = canonical_json_from_record({"t": composed})

    assert json1 == json2
    # ensure it is the composed form in the string
    assert composed in json1


def test_canonical_json_arrays():
    """Test that arrays preserve order."""
    data = {"arr": [2, 1, 3]}
    canonical = canonical_json_from_record(data)
    assert canonical == '{"arr":[2,1,3]}'


def test_hasher_impl_business_key():
    """Test business key hashing via HasherImpl."""
    record = {"id": 100, "type": "assay", "ignored": "val"}
    fields = ["id", "type"]

    df = pd.DataFrame([record])
    hasher = HasherImpl()

    # Hash columns
    # Should produce hash of canonical json of [100, "assay"]
    hashes = hasher.hash_columns(df, fields)
    h = hashes.iloc[0]

    assert len(h) == 64

    # Verify against manual
    manual_serialized = canonical_json_from_record([100, "assay"])
    manual_hash = blake2b_hash_hex(manual_serialized.encode("utf-8"))
    assert h == manual_hash

    # Order matters
    h_rev_series = hasher.hash_columns(df, ["type", "id"])
    h_rev = h_rev_series.iloc[0]
    assert h != h_rev


def test_hasher_impl_row_hash():
    """Test row hashing via HasherImpl."""
    record = {"a": 1, "b": 2}
    df = pd.DataFrame([record])
    hasher = HasherImpl()

    # Hash row
    # We have to apply it manually or check logic
    # HashService uses: df.apply(hasher.hash_row, axis=1)
    h = hasher.hash_row(df.iloc[0])

    assert len(h) == 64

    # Manual check
    # Note: HasherImpl.hash_row does .to_dict() on the series.
    # pd.Series({"a":1}).to_dict() -> {"a": 1} (types preserved mostly)
    manual_serialized = canonical_json_from_record(record)
    manual_hash = blake2b_hash_hex(manual_serialized.encode("utf-8"))
    assert h == manual_hash


def test_blake2b_algorithm_sanity():
    """Sanity check for BLAKE2b."""
    # Empty string blake2b-256 hex
    import hashlib

    expected = hashlib.blake2b(b"", digest_size=32).hexdigest()
    assert blake2b_hash_hex(b"") == expected


def test_golden_examples():
    """
    Run golden examples.
    """
    golden_path = Path(__file__).parent / "golden_examples.json"
    if not golden_path.exists():
        pytest.skip("Golden examples file not found")

    with open(golden_path, "r", encoding="utf-8") as f:
        examples = json.load(f)

    hasher = HasherImpl()

    for ex in examples:
        record = ex["input_record"]
        bk_fields = ex["business_key_fields"]

        # Calculate BK Hash manually to match old logic (list of values)
        # Simulate what hash_columns does for a single row
        bk_values = []
        # Note: compute_hash_business_key returns None if field missing.
        # HasherImpl.hash_columns behavior: if we use df, we get columns.
        # If record is missing key, and we make DF, we get NaN?
        # Golden examples are well formed.
        bk_values = [record.get(f) for f in bk_fields]
        bk_serialized = canonical_json_from_record(bk_values)
        bk_hash = blake2b_hash_hex(bk_serialized.encode("utf-8"))

        # Inject bk hash for row hash calculation
        record_with_hash = record.copy()
        record_with_hash["hash_business_key"] = bk_hash

        # Calculate Row Hash
        # Use HasherImpl.hash_row
        row_series = pd.Series(record_with_hash)
        row_hash = hasher.hash_row(row_series)

        # Assertions if expected provided
        expected_bk = ex.get("expected_hash_business_key")
        if expected_bk and "TO BE FILLED" not in expected_bk:
            assert bk_hash == expected_bk, f"BK Hash mismatch for {ex['description']}"

        expected_row = ex.get("expected_hash_row")
        if expected_row and "TO BE FILLED" not in expected_row:
            assert (
                row_hash == expected_row
            ), f"Row Hash mismatch for {ex['description']}"
