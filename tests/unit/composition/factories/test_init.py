"""Unit tests for ``bioetl.composition.factories`` lazy package exports."""

from __future__ import annotations

import types

import pytest


@pytest.mark.unit
def test_factory_root_exports_from_map_via_import_module(monkeypatch):
    """Mapped exports should be loaded from their configured module."""
    import bioetl.composition.factories as factories_pkg

    calls: list[str] = []

    def _fake_import_module(name: str) -> object:
        calls.append(name)
        if name == "bioetl.composition.factories.services.factory":
            return types.SimpleNamespace(
                BaseServicesFactory="base_service_factory",
                DataSourceCreatorProtocol="creator_protocol",
            )
        if name == "bioetl.composition.factories.datasource.data_source_factory":
            return types.SimpleNamespace(
                DataSourceCreatorProtocol="creator_protocol",
            )
        raise AssertionError(f"Unexpected import module: {name}")

    monkeypatch.setattr(factories_pkg, "import_module", _fake_import_module)

    assert factories_pkg.BaseServicesFactory == "base_service_factory"
    assert factories_pkg.DataSourceCreatorProtocol == "creator_protocol"
    assert calls == [
        "bioetl.composition.factories.services.factory",
        "bioetl.composition.factories.datasource.data_source_factory",
    ]
    # second access should use cached value for map-backed names
    assert factories_pkg.BaseServicesFactory == "base_service_factory"
    assert calls == [
        "bioetl.composition.factories.services.factory",
        "bioetl.composition.factories.datasource.data_source_factory",
    ]


@pytest.mark.unit
def test_factory_root_exports_load_pipeline_modules_without_import_module(monkeypatch):
    """Pipeline-export branch should resolve symbols from factory pipeline submodules."""
    import bioetl.composition.factories as factories_pkg

    fake_runner = types.SimpleNamespace(name="fake_runner")
    fake_factory = types.SimpleNamespace(name="fake_factory")
    import bioetl.composition.factories.pipeline as pipeline_module
    from bioetl.composition.factories.pipeline import registry as registry_module

    monkeypatch.setattr(pipeline_module, "assemble_runner", fake_runner)
    monkeypatch.setattr(registry_module, "chembl_activity_factory", fake_factory)

    assert factories_pkg.assemble_runner is fake_runner
    assert factories_pkg.chembl_activity_factory is fake_factory


@pytest.mark.unit
def test_factory_root_unknown_attribute_raises_attribute_error() -> None:
    """Unknown exports must raise AttributeError."""
    import bioetl.composition.factories as factories_pkg

    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(factories_pkg, "not_in_factory_exports")
