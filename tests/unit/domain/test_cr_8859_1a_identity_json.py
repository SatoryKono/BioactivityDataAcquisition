# pyright: reportArgumentType=false

"""Focused tests for CR-FULL 20260816 identity/JSON residuals (#8891)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta, timezone

import pytest

from bioetl.domain.deterministic_identity import deterministic_id
from bioetl.domain.normalization._control_plane_payloads import (
    _normalize_manifest_input_snapshots,
)
from bioetl.domain.normalization._hash_identity_scalars import (
    normalize_hash_scalar_for_policy,
)
from bioetl.domain.normalization.fingerprints import (
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.domain.normalization.json import serialize_json_canonical
from bioetl.domain.normalization.profiles._profile_textual_normalizers import (
    normalize_profile_json_string_unordered_collection,
)
from bioetl.domain.serialization import serialize_to_json

pytestmark = pytest.mark.unit


def test_deterministic_identity_rejects_non_string_mapping_keys() -> None:
    with pytest.raises(TypeError, match="string keys"):
        deterministic_id("scope", {1: "value"})
    with pytest.raises(TypeError, match="string keys"):
        deterministic_id("scope", {"outer": {1: "value"}})


def test_serialize_to_json_emits_utf16_surrogate_pairs() -> None:
    result = serialize_to_json({"emoji": "👋"})
    assert result == '{"emoji":"\\ud83d\\udc4b"}'


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_serialize_to_json_rejects_non_finite_before_backend(value: float) -> None:
    with pytest.raises(ValueError, match="does not allow NaN or Infinity"):
        serialize_to_json({"value": value})


def test_manifest_snapshot_sort_coerces_non_text_snapshot_id() -> None:
    snapshots = [
        {"snapshot_id": 2, "label": "b"},
        {"snapshot_id": None, "label": "z"},
        {"snapshot_id": 1, "label": "a"},
    ]
    ordered = _normalize_manifest_input_snapshots(snapshots)
    assert [item["label"] for item in ordered] == ["z", "a", "b"]


def test_hash_scalar_canonicalizes_signed_zero() -> None:
    positive = normalize_hash_scalar_for_policy(-0.0, datetime_policy="v2_datetime_utc")
    negative = normalize_hash_scalar_for_policy(0.0, datetime_policy="v2_datetime_utc")
    assert positive == 0.0
    assert negative == 0.0
    assert math.copysign(1.0, positive) == 1.0
    assert math.copysign(1.0, negative) == 1.0


def test_invalid_unordered_json_keeps_trimmed_string() -> None:
    result = normalize_profile_json_string_unordered_collection("  not-json  ")
    assert result == "not-json"


def test_snapshot_fingerprint_treats_naive_and_utc_equivalent() -> None:
    naive = datetime(2026, 1, 2, 3, 4, 5)
    aware = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    offset = datetime(2026, 1, 2, 6, 4, 5, tzinfo=timezone(timedelta(hours=3)))
    naive_hash = compute_input_snapshot_identity_fingerprint(
        [{"snapshot_id": "s1", "captured_at": naive}]
    )
    aware_hash = compute_input_snapshot_identity_fingerprint(
        [{"snapshot_id": "s1", "captured_at": aware}]
    )
    offset_hash = compute_input_snapshot_identity_fingerprint(
        [{"snapshot_id": "s1", "captured_at": offset}]
    )
    assert naive_hash == aware_hash == offset_hash


def test_canonical_json_rejects_numpy_arrays() -> None:
    numpy = pytest.importorskip("numpy")
    with pytest.raises(TypeError, match="requires JSON-compatible values"):
        serialize_json_canonical(numpy.array([1.0, math.nan]))
