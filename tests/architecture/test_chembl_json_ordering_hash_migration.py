"""Architecture guard for reviewed ChEMBL JSON ordering policy identity."""

from __future__ import annotations

from bioetl.domain.normalization.profiles.chembl_json_ordering_policy import (
    CHEMBL_JSON_ORDERING_POLICY_HASH,
    CHEMBL_JSON_ORDERING_POLICY_VERSION,
)


def test_chembl_json_ordering_policy_changes_require_explicit_version_and_hash_review() -> (
    None
):
    assert CHEMBL_JSON_ORDERING_POLICY_VERSION == "2026.05.30"
    assert (
        CHEMBL_JSON_ORDERING_POLICY_HASH
        == "7ee2e7b8490c86411c9f124080b0e9346fe0596f0b41ecdd69553a9097afec1b"
    )
