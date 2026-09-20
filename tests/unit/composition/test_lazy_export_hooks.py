"""Behavioral coverage for composition lazy-export hook builders (AUD-009)."""

from __future__ import annotations

import math
import sys

import pytest

from bioetl.composition.lazy_exports import (
    build_lazy_export_hooks,
    install_cached_public_exports,
    lazy_export_dir,
    resolve_lazy_callable,
    resolve_lazy_export,
)


pytestmark = pytest.mark.unit

_EXPORTS = {"pi": ("math", "pi"), "py_version": ("sys", "version")}


def test_resolve_lazy_export_returns_target_without_caching_by_default() -> None:
    namespace: dict[str, object] = {}
    assert (
        resolve_lazy_export(
            module_globals=namespace,
            public_exports=_EXPORTS,
            module_name="sentinel_module",
            name="pi",
        )
        == math.pi
    )
    assert namespace == {}


def test_resolve_lazy_export_caches_when_requested() -> None:
    namespace: dict[str, object] = {}
    value = resolve_lazy_export(
        module_globals=namespace,
        public_exports=_EXPORTS,
        module_name="sentinel_module",
        name="py_version",
        cache=True,
    )
    assert value == sys.version
    assert namespace["py_version"] == sys.version


def test_resolve_lazy_export_unknown_name_raises() -> None:
    with pytest.raises(AttributeError, match="has no attribute"):
        resolve_lazy_export(
            module_globals={},
            public_exports=_EXPORTS,
            module_name="sentinel_module",
            name="does_not_exist",
        )


def test_build_lazy_export_hooks_resolve_and_list() -> None:
    namespace: dict[str, object] = {"explicit": 1}
    getattr_hook, dir_hook = build_lazy_export_hooks(
        module_globals=namespace,
        public_exports=_EXPORTS,
        module_name="sentinel_module",
        explicit_exports=["explicit"],
        cache=True,
    )
    assert getattr_hook("pi") == math.pi
    assert namespace["pi"] == math.pi
    listed = dir_hook()
    assert {"pi", "py_version", "explicit"} <= set(listed)
    assert listed == sorted(listed)
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr_hook("does_not_exist")


def test_lazy_export_dir_unions_and_sorts() -> None:
    assert lazy_export_dir(
        module_globals={"b": 1},
        public_exports={"a": ("math", "pi")},
        explicit_exports=["c"],
    ) == ["a", "b", "c"]


def test_resolve_plain_string_target_uses_export_name_as_attr() -> None:
    assert (
        resolve_lazy_export(
            module_globals={},
            public_exports={"version": "sys"},
            module_name="sentinel_module",
            name="version",
        )
        == sys.version
    )


def test_resolve_lazy_callable_returns_target() -> None:
    assert resolve_lazy_callable("math", "pi") == math.pi


def test_install_cached_public_exports_resolves_and_caches() -> None:
    namespace: dict[str, object] = {}
    install_cached_public_exports(
        module_globals=namespace,
        public_exports=_EXPORTS,
        module_name="sentinel_module",
    )
    getattr_hook = namespace["__getattr__"]
    assert callable(getattr_hook)
    assert getattr_hook("pi") == math.pi  # type: ignore[operator]
    assert namespace["pi"] == math.pi
