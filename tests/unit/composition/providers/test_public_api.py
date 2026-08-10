"""Regression tests for the lazy provider package public API."""

from __future__ import annotations

import pytest

import bioetl.composition.providers as providers


pytestmark = pytest.mark.unit


def test_provider_package_rejects_unknown_lazy_export() -> None:
    """Unknown symbols fail with the normal module-level AttributeError contract."""
    with pytest.raises(AttributeError, match="has no attribute 'missing_provider_api'"):
        getattr(providers, "missing_provider_api")


def test_provider_package_dir_includes_declared_lazy_exports() -> None:
    """Interactive discovery exposes every declared public lazy export."""
    assert set(providers.__all__) <= set(dir(providers))
