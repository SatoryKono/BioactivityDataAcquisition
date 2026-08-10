"""Directory-discovery contracts for lazy domain facades."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit


def _facade_dir(module_name: str) -> tuple[ModuleType, list[str]]:
    module = import_module(module_name)
    return module, list(module.__dir__())


def test_ports_dir_contains_every_public_lazy_export() -> None:
    """Interactive discovery includes all declared port facade exports."""
    ports, names = _facade_dir("bioetl.domain.ports")

    assert names == sorted(set(names))
    assert set(ports.__all__) <= set(names)


def test_types_dir_contains_every_public_lazy_export() -> None:
    """Interactive discovery includes all declared domain type exports."""
    types, names = _facade_dir("bioetl.domain.types")

    assert names == sorted(set(names))
    assert set(types.__all__) <= set(names)
