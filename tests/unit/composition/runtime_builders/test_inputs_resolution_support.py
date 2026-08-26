"""Unit tests for runtime input resolution support."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from bioetl.composition.runtime_builders._inputs_resolution_support import (
    apply_tracing_override,
)
from bioetl.infrastructure.config._base import Settings


pytestmark = pytest.mark.unit


def test_apply_tracing_override_without_observability_returns_original() -> None:
    """Minimal settings objects have no tracing surface to override."""
    settings = cast(Settings, SimpleNamespace())

    assert apply_tracing_override(settings=settings, enabled=True) is settings
