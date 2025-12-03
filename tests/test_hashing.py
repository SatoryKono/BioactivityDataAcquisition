import json
import pytest
from pathlib import Path
from decimal import Decimal
from bioetl.domain.hashing.hash_calculator import (
    canonical_json_from_record,
    compute_hash_business_key,
    compute_hash_row,
    blake2b_hash_hex
)

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
    decomposed = 'cafe\u0301'
    composed = 'caf\u00e9'
    
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
    # remove space in assertion if my implementation doesn't add space
    # My impl: "[" + ",".join(items) + "]" -> no spaces
    assert canonical == '{"arr":[2,1,3]}'

def test_compute_hash_business_key():
    """Test business key hashing."""
    record = {"id": 100, "type": "assay", "ignored": "val"}
    fields = ["id", "type"]
    
    # Serialized: [100,"assay"]
    # BLAKE2b([100,"assay"])
    
    h = compute_hash_business_key(record, fields)
    assert len(h) == 64
    
    # Order matters in definition
    h_rev = compute_hash_business_key(record, ["type", "id"])
    assert h != h_rev

def test_blake2b_algorithm_sanity():
    """Sanity check for BLAKE2b."""
    # Empty string blake2b-256 hex
    # b'' -> 
    import hashlib
    expected = hashlib.blake2b(b'', digest_size=32).hexdigest()
    assert blake2b_hash_hex(b'') == expected

def test_golden_examples():
    """
    Run golden examples. 
    Currently just checks that we can run without error, 
    and if expected hashes are present (non-empty), checks them.
    """
    golden_path = Path(__file__).parent / "golden_examples.json"
    if not golden_path.exists():
        pytest.skip("Golden examples file not found")
        
    with open(golden_path, "r", encoding="utf-8") as f:
        examples = json.load(f)
        
    for ex in examples:
        record = ex["input_record"]
        bk_fields = ex["business_key_fields"]
        
        # Calculate
        bk_hash = compute_hash_business_key(record, bk_fields)
        
        # Inject bk hash for row hash calculation
        record_with_hash = record.copy()
        record_with_hash["hash_business_key"] = bk_hash
        
        row_hash = compute_hash_row(record_with_hash)
        
        # Assertions if expected provided
        expected_bk = ex.get("expected_hash_business_key")
        if expected_bk and "TO BE FILLED" not in expected_bk:
            assert bk_hash == expected_bk, f"BK Hash mismatch for {ex['description']}"
            
        expected_row = ex.get("expected_hash_row")
        if expected_row and "TO BE FILLED" not in expected_row:
            assert row_hash == expected_row, f"Row Hash mismatch for {ex['description']}"

