"""Unit tests for lazy domain-port facade construction."""

from __future__ import annotations

import pytest

from bioetl.domain.ports._facade_support import build_export_modules


pytestmark = pytest.mark.unit


def test_build_export_modules_maps_exports_and_allows_same_module_duplicates() -> None:
    assert build_export_modules(
        {
            "bioetl.domain.ports.alpha": ("AlphaPort", "SharedPort", "SharedPort"),
            "bioetl.domain.ports.beta": ("BetaPort",),
        }
    ) == {
        "AlphaPort": "bioetl.domain.ports.alpha",
        "SharedPort": "bioetl.domain.ports.alpha",
        "BetaPort": "bioetl.domain.ports.beta",
    }


def test_build_export_modules_rejects_cross_module_collisions() -> None:
    with pytest.raises(RuntimeError, match="duplicate ports export 'SharedPort'"):
        build_export_modules(
            {
                "bioetl.domain.ports.alpha": ("SharedPort",),
                "bioetl.domain.ports.beta": ("SharedPort",),
            }
        )
