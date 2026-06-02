"""Unit tests for application-owned record normalization stage."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.application.core.config import (
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    NormalizationContractError,
    RecordNormalizationProcessor,
)


@pytest.mark.unit
def build_normalization_processor(**kwargs):
    return RecordNormalizationProcessor(**kwargs)


__all__ = [
    "ContentHashPolicyByVersion",
    "ContentHashVersionPolicy",
    "HealthCheck",
    "MagicMock",
    "NormalizationContractError",
    "PreSilverRecord",
    "build_normalization_processor",
    "cast",
    "given",
    "pytest",
    "settings",
    "st",
]
