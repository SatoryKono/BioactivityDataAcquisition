"""Unit tests for shared composition lazy-export helpers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bioetl.composition._lazy_exports import lazy_export_dir, resolve_lazy_export


pytestmark = pytest.mark.unit


def test_resolve_lazy_export_returns_value_without_caching() -> None:
    module_globals: dict[str, object] = {}
    public_exports = {"demo": "bioetl.fake.module"}
    expected = object()

    with patch("bioetl.composition._lazy_exports.import_module") as mock_import_module:
        mock_import_module.return_value = type("FakeModule", (), {"demo": expected})()

        result = resolve_lazy_export(
            module_globals=module_globals,
            public_exports=public_exports,
            module_name="bioetl.example",
            name="demo",
        )

    assert result is expected
    assert "demo" not in module_globals


def test_resolve_lazy_export_caches_value_when_requested() -> None:
    module_globals: dict[str, object] = {}
    public_exports = {"demo": "bioetl.fake.module"}
    expected = object()

    with patch("bioetl.composition._lazy_exports.import_module") as mock_import_module:
        mock_import_module.return_value = type("FakeModule", (), {"demo": expected})()

        result = resolve_lazy_export(
            module_globals=module_globals,
            public_exports=public_exports,
            module_name="bioetl.example",
            name="demo",
            cache=True,
        )

    assert result is expected
    assert module_globals["demo"] is expected


def test_resolve_lazy_export_raises_attribute_error_for_unknown_name() -> None:
    with pytest.raises(AttributeError, match="bioetl.example"):
        resolve_lazy_export(
            module_globals={},
            public_exports={},
            module_name="bioetl.example",
            name="missing",
        )


def test_lazy_export_dir_merges_globals_public_and_explicit_exports() -> None:
    names = lazy_export_dir(
        module_globals={"existing": object()},
        public_exports={"lazy_export": "bioetl.fake.module"},
        explicit_exports=("explicit_export",),
    )

    assert names == ["existing", "explicit_export", "lazy_export"]
