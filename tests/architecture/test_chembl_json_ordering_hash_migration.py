"""Architecture guard for reviewed ChEMBL JSON ordering policy identity."""

from __future__ import annotations

from bioetl.domain.normalization.profiles.chembl_json_ordering_policy import (
    CHEMBL_JSON_ORDERING_POLICY_HASH,
    CHEMBL_JSON_ORDERING_POLICY_VERSION,
)


def test_chembl_json_ordering_policy_changes_require_explicit_version_and_hash_review() -> (
    None
):
    assert CHEMBL_JSON_ORDERING_POLICY_VERSION == "2026.05.12"
    assert (
        CHEMBL_JSON_ORDERING_POLICY_HASH
        == "92feb6dd5b391a189fc0b71f996841f35e302df0c05d1e4f9df5dd4f5e953625"
    )
