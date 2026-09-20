"""Stream B DOM: leftover Gold reject taxonomy branches."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.domain.types._gold_contracts_support import GOLD_CONTRACT_VERSION_UNKNOWN
from bioetl.domain.types.gold_contracts_rejects import (
    GoldRejectReasonCode,
    _extract_version_from_to_schema,
    _known_contract_version_or_none,
    classify_gold_schema_error_reason,
)

pytestmark = pytest.mark.unit


def test_classify_schema_error_defaults_to_schema_failure() -> None:
    assert (
        classify_gold_schema_error_reason(ValueError("type mismatch"))
        is GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE
    )


def test_unknown_contract_version_is_dropped() -> None:
    assert _known_contract_version_or_none(GOLD_CONTRACT_VERSION_UNKNOWN) is None
    assert _known_contract_version_or_none("1.2.3") == "1.2.3"


def test_extract_version_via_to_schema_delegate() -> None:
    inner = SimpleNamespace(version="9.9.9")
    outer = SimpleNamespace(to_schema=lambda: inner, metadata=None, Config=None)
    assert _extract_version_from_to_schema(outer) == "9.9.9"
