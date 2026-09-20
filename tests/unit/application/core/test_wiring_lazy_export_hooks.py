"""Behavioral coverage for wiring lazy-export hooks (AUD-009)."""

from __future__ import annotations

import math

import pytest

from bioetl.application.core.wiring.lazy_export_hooks import (
    install_lazy_export_facade,
    lazy_export_dir,
    resolve_lazy_export,
)


pytestmark = pytest.mark.unit

_EXPORTS = {"pi": ("math", "pi")}


def test_resolve_lazy_export_caches_into_namespace() -> None:
    namespace: dict[str, object] = {}
    value = resolve_lazy_export(
        module_name="sentinel_module",
        public_exports=_EXPORTS,
        name="pi",
        namespace=namespace,
    )
    assert value == math.pi
    assert namespace["pi"] == math.pi


def test_resolve_lazy_export_unknown_name_raises_wiring() -> None:
    with pytest.raises(AttributeError, match="has no attribute"):
        resolve_lazy_export(
            module_name="sentinel_module",
            public_exports=_EXPORTS,
            name="does_not_exist",
            namespace={},
        )


def test_install_lazy_export_facade_wires_hooks() -> None:
    namespace: dict[str, object] = {}
    install_lazy_export_facade(namespace, "sentinel_module", _EXPORTS)
    assert namespace["__all__"] == ["pi"]
    getattr_hook = namespace["__getattr__"]
    dir_hook = namespace["__dir__"]
    assert callable(getattr_hook) and callable(dir_hook)
    assert getattr_hook("pi") == math.pi  # type: ignore[operator]
    assert "pi" in dir_hook()  # type: ignore[operator]
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr_hook("does_not_exist")  # type: ignore[operator]


def test_lazy_export_dir_unions_and_sorts_wiring() -> None:
    assert lazy_export_dir({"b": 1}, ["a"]) == ["a", "b"]
