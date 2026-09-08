"""The credential regression helper retains exact substring detection."""

import hashlib

import pytest

from tests.helpers.secret_fingerprints import contains_secret_fingerprint

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("synthetic-test-value", True),
        ("prefixsynthetic-test-valuesuffix", True),
        ('AUTH="user/synthetic-test-value"', True),
        ("synthetic-test-ValuE", False),
        ("synthetic test value", False),
        ("unrelated content", False),
    ],
)
def test_fingerprint_helper_preserves_exact_substring_matching(
    content: str, expected: bool
) -> None:
    example = b"synthetic-test-value"
    fingerprints = ((len(example), hashlib.sha256(example).hexdigest()),)

    assert contains_secret_fingerprint(content, fingerprints) is expected
