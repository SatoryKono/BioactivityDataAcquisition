"""Focused contracts for pipeline context composition."""

from __future__ import annotations

import pytest

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    _build_vacuum_config,
)

pytestmark = pytest.mark.unit


def test_vacuum_retention_none_defaults_without_coercing_explicit_zero() -> None:
    options_none = RunOptions(vacuum_after_run=True, vacuum_retention_days=None)
    assert _build_vacuum_config(options_none).retention_days == 7

    options_zero = RunOptions(vacuum_after_run=True, vacuum_retention_days=0)
    with pytest.raises(ValueError, match="retention_days must be positive"):
        _build_vacuum_config(options_zero)
