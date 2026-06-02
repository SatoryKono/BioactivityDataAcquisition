"""Tests for resolve_bronze_opts helper function.

Tests tri-state resolution logic for per-phase cached Bronze settings
in composite pipeline bootstrap.
"""

from __future__ import annotations

import pytest

from bioetl.application.composite.runner_pkg import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
    resolve_bronze_opts as _resolve_bronze_opts,
)


pytestmark = pytest.mark.unit


class TestResolveBronzeOpts:
    """Test _resolve_bronze_opts tri-state resolution."""

    def test_none_override_follows_master_true(self) -> None:
        """None override follows master switch when True."""
        runtime = CompositeRuntimeConfig(use_cached_bronze=True)
        result = _resolve_bronze_opts(runtime, phase_override=None)
        assert result["use_cached_bronze"] is True

    def test_none_override_follows_master_false(self) -> None:
        """None override follows master switch when False."""
        runtime = CompositeRuntimeConfig(use_cached_bronze=False)
        result = _resolve_bronze_opts(runtime, phase_override=None)
        assert result["use_cached_bronze"] is False

    def test_true_override_forces_cache(self) -> None:
        """True override forces cache even when master is False."""
        runtime = CompositeRuntimeConfig(use_cached_bronze=False)
        result = _resolve_bronze_opts(runtime, phase_override=True)
        assert result["use_cached_bronze"] is True

    def test_false_override_forces_api(self) -> None:
        """False override forces API even when master is True."""
        runtime = CompositeRuntimeConfig(use_cached_bronze=True)
        result = _resolve_bronze_opts(runtime, phase_override=False)
        assert result["use_cached_bronze"] is False

    def test_path_cleared_when_cache_disabled(self) -> None:
        """Bronze path/date should be None when cache is disabled."""
        runtime = CompositeRuntimeConfig(
            use_cached_bronze=True,
            cached_bronze_path="/some/path",
            cached_bronze_date="2026-01-01",
        )
        result = _resolve_bronze_opts(runtime, phase_override=False)
        assert result["use_cached_bronze"] is False
        assert result["cached_bronze_path"] is None
        assert result["cached_bronze_date"] is None

    def test_path_preserved_when_cache_enabled(self) -> None:
        """Bronze path/date should be preserved when cache is enabled."""
        runtime = CompositeRuntimeConfig(
            use_cached_bronze=True,
            cached_bronze_path="/some/path",
            cached_bronze_date="2026-01-01",
        )
        result = _resolve_bronze_opts(runtime, phase_override=None)
        assert result["use_cached_bronze"] is True
        assert result["cached_bronze_path"] == "/some/path"
        assert result["cached_bronze_date"] == "2026-01-01"

    def test_path_provided_when_override_enables(self) -> None:
        """Bronze path/date provided when phase override enables cache."""
        runtime = CompositeRuntimeConfig(
            use_cached_bronze=False,
            cached_bronze_path="/some/path",
            cached_bronze_date="2026-01-01",
        )
        result = _resolve_bronze_opts(runtime, phase_override=True)
        assert result["use_cached_bronze"] is True
        assert result["cached_bronze_path"] == "/some/path"
        assert result["cached_bronze_date"] == "2026-01-01"

    def test_dependencies_default_to_api(self) -> None:
        """Dependencies default to False (API) even when master is True."""
        runtime = CompositeRuntimeConfig(use_cached_bronze=True)
        assert runtime.use_cached_bronze is True
        assert runtime.cached_bronze_dependencies is False
        result = _resolve_bronze_opts(
            runtime, phase_override=runtime.cached_bronze_dependencies
        )
        assert result["use_cached_bronze"] is False
