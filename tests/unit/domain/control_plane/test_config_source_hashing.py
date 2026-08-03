# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for canonical config source hashing."""

from __future__ import annotations

import hashlib

import pytest

from bioetl.domain.control_plane.config_source_hashing import (
    compute_canonical_yaml_sha256,
    compute_config_source_hashes,
)


pytestmark = pytest.mark.unit


def test_canonical_yaml_hash_ignores_comments_and_key_order() -> None:
    first = b"""
    # formatting-only noise
    pipeline:
      name: chembl_activity
      version: 1
    settings:
      batch_size: 1000
    """
    second = b"""
    settings: {batch_size: 1000}
    pipeline:
      version: 1
      name: chembl_activity
    """

    assert compute_canonical_yaml_sha256(first) == compute_canonical_yaml_sha256(second)
    assert hashlib.sha256(first).hexdigest() != hashlib.sha256(second).hexdigest()


def test_canonical_yaml_hash_changes_for_semantic_value_change() -> None:
    first = b"pipeline:\n  version: 1\n"
    second = b"pipeline:\n  version: 2\n"

    assert compute_canonical_yaml_sha256(first) != compute_canonical_yaml_sha256(second)


def test_canonical_yaml_hash_rejects_duplicate_mapping_keys() -> None:
    with pytest.raises(ValueError, match="Duplicate YAML mapping key"):
        compute_canonical_yaml_sha256(b"pipeline:\n  version: 1\n  version: 2\n")


def test_config_source_hashes_preserve_raw_hash_separately() -> None:
    raw_bytes = b"pipeline:\n  version: 1\n"

    hashes = compute_config_source_hashes(
        source_path="configs/base/pipeline.yaml",
        raw_bytes=raw_bytes,
    )

    assert hashes.hash_strategy == "canonical_yaml"
    assert hashes.semantic_hash == compute_canonical_yaml_sha256(raw_bytes)
    assert hashes.raw_hash == hashlib.sha256(raw_bytes).hexdigest()


def test_non_yaml_source_hash_uses_raw_bytes_as_semantic_identity() -> None:
    raw_bytes = b'{"pipeline":{"version":1}}\n'

    hashes = compute_config_source_hashes(
        source_path="configs/base/pipeline.json",
        raw_bytes=raw_bytes,
    )

    assert hashes.hash_strategy == "raw_bytes"
    assert hashes.semantic_hash == hashlib.sha256(raw_bytes).hexdigest()
    assert hashes.raw_hash == hashes.semantic_hash
