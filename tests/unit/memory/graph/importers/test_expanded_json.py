import pytest

from memory.graph.importers.expanded_json import (
    _explicit_path_refs,
    _extract_adr_lifecycle_field,
    _failure_mode_name,
    _slugify,
)


pytestmark = pytest.mark.unit

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


def test_explicit_path_refs_extracts_prefixed_paths_without_regex_dependency():
    text = """
    - docs/02-architecture/decisions/ADR-001.md constrains src/bioetl/app.py.
    - configs/providers/chembl.yaml, tests/unit/sample_test.py)
    """

    assert _explicit_path_refs(text) == {
        "docs/02-architecture/decisions/ADR-001.md",
        "src/bioetl/app.py",
        "configs/providers/chembl.yaml",
        "tests/unit/sample_test.py",
    }


def test_explicit_path_refs_handles_large_non_matching_input():
    text = "x" * 10000 + " docs/02-architecture/decisions/ADR-002.md"
    assert _explicit_path_refs(text) == {"docs/02-architecture/decisions/ADR-002.md"}


def test_failure_mode_name_valid():
    assert (
        _failure_mode_name("Some Failure Mode (XYZ)", "fallback") == "Some Failure Mode"
    )
    assert _failure_mode_name("Some Error Runbook", "fallback") == "Some Error"
    assert _failure_mode_name("Some Error (XYZ) Runbook", "fallback") == "Some Error"
    assert (
        _failure_mode_name("Some Error Runbook (XYZ)", "fallback")
        == "Some Error Runbook"
    )


def test_failure_mode_name_fallback():
    assert _failure_mode_name("", "fallback-stem") == "fallback stem"


def test_failure_mode_name_adversarial():
    # Large inputs
    large_input = "A" * 10000 + " (XYZ) runbook"
    assert _failure_mode_name(large_input, "fallback") == "A" * 10000


def test_slugify_collapses_non_alnum_runs_without_regex():
    assert _slugify("Some Failure Mode (XYZ)") == "some-failure-mode-xyz"


def test_slugify_handles_large_input_deterministically():
    assert _slugify("A" * 10000 + " !!!") == ("a" * 10000)
