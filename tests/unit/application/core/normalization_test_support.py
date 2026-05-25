"""Unit tests for application-owned record normalization stage."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast
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
from bioetl.domain.transformations import generate_content_hash

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


@pytest.mark.unit


def build_normalization_processor(**kwargs):
    return RecordNormalizationProcessor(**kwargs)


__all__ = [
    name
    for name in globals()
    if name
    not in {
        "__builtins__",
        "__cached__",
        "__doc__",
        "__file__",
        "__loader__",
        "__name__",
        "__package__",
        "__spec__",
    }
]
