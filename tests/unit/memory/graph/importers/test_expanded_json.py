from memory.graph.importers.expanded_json import _extract_adr_lifecycle_field, _failure_mode_name

def test_extract_adr_lifecycle_field_valid():
    assert _extract_adr_lifecycle_field("* supersedes:") == "supersedes"
    assert _extract_adr_lifecycle_field(" -  superseded by :") == "superseded by"
    assert _extract_adr_lifecycle_field("> amends:") == "amends"
    assert _extract_adr_lifecycle_field("`amended by`:") == "amended by"

def test_extract_adr_lifecycle_field_invalid():
    assert _extract_adr_lifecycle_field("supersedes") is None
    assert _extract_adr_lifecycle_field("* not a field: ") is None
    assert _extract_adr_lifecycle_field("") is None

def test_extract_adr_lifecycle_field_adversarial():
    # Long strings should not cause catastrophic backtracking
    long_prefix = "*" * 10000 + " supersedes:"
    assert _extract_adr_lifecycle_field(long_prefix) == "supersedes"

def test_failure_mode_name_valid():
    assert _failure_mode_name("Some Failure Mode (XYZ)", "fallback") == "Some Failure Mode"
    assert _failure_mode_name("Some Error Runbook", "fallback") == "Some Error"
    assert _failure_mode_name("Some Error (XYZ) Runbook", "fallback") == "Some Error"
    assert _failure_mode_name("Some Error Runbook (XYZ)", "fallback") == "Some Error Runbook"

def test_failure_mode_name_fallback():
    assert _failure_mode_name("", "fallback-stem") == "fallback stem"

def test_failure_mode_name_adversarial():
    # Large inputs
    large_input = "A" * 10000 + " (XYZ) runbook"
    assert _failure_mode_name(large_input, "fallback") == "A" * 10000
