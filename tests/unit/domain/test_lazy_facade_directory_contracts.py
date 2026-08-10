"""Directory-discovery contracts for lazy domain facades."""

from __future__ import annotations

import pytest

from bioetl.domain import ports, types

pytestmark = pytest.mark.unit


def test_ports_dir_contains_every_public_lazy_export() -> None:
    """Interactive discovery includes all declared port facade exports."""
    names = ports.__dir__()

    assert names == sorted(set(names))
    assert set(ports.__all__) <= set(names)


def test_types_dir_contains_every_public_lazy_export() -> None:
    """Interactive discovery includes all declared domain type exports."""
    names = types.__dir__()

    assert names == sorted(set(names))
    assert set(types.__all__) <= set(names)
