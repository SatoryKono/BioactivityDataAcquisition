"""Unit tests for ``bioetl.composition.bootstrap.cli`` package lazy exports."""

from __future__ import annotations

import types

from pathlib import Path

import pytest


@pytest.mark.unit
def test_bootstrap_adr_service_uses_filesystem_catalog(monkeypatch):
    """CLI ADR bootstrap should use ``FilesystemAdrCatalog``."""
    from bioetl.infrastructure.adr import fs_adr_service

    fake_service = object()

    monkeypatch.setattr(fs_adr_service, "FilesystemAdrCatalog", lambda: fake_service)
    import bioetl.composition.bootstrap.cli as cli_pkg

    assert cli_pkg.bootstrap_adr_service() is fake_service


@pytest.mark.unit
def test_bootstrap_control_plane_lifecycle_store_builds_expected_path(
    monkeypatch, tmp_path: Path
):
    """Lifecycle store bootstrap should resolve ``<data_dir>/output/control`` path."""
    from types import SimpleNamespace

    captured: dict[str, object] = {}

    class _FakeStore:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    class _FakeLogger:
        pass

    class _FakeMetrics:
        pass

    from bioetl.composition.runtime_builders import config_access
    from bioetl.infrastructure import control_plane
    from bioetl.infrastructure.observability import noop_logger
    from bioetl.domain.ports import noop as noop_port

    monkeypatch.setattr(
        config_access,
        "get_settings",
        lambda: SimpleNamespace(data_dir=str(tmp_path / "data")),
    )
    monkeypatch.setattr(
        control_plane, "FileControlPlaneArtifactLifecycleStore", _FakeStore
    )
    monkeypatch.setattr(noop_logger, "NoOpLogger", _FakeLogger)
    monkeypatch.setattr(noop_port, "NoOpMetrics", _FakeMetrics)

    import bioetl.composition.bootstrap.cli as cli_pkg

    store = cli_pkg.bootstrap_control_plane_lifecycle_store()

    assert store is not None
    assert captured["base_path"] == tmp_path / "data" / "output" / "control"
    assert isinstance(captured["logger"], _FakeLogger)
    assert isinstance(captured["metrics"], _FakeMetrics)


@pytest.mark.unit
def test_lazy_export_loads_declared_target_module(monkeypatch):
    """``__getattr__`` should resolve mapped module symbols lazily."""
    from bioetl.composition.bootstrap import cli as cli_pkg

    loader_calls: list[str] = []
    expected = object()

    def _fake_import_module(name: str) -> object:
        loader_calls.append(name)
        if name == "bioetl.composition.bootstrap.cli.health":
            return types.SimpleNamespace(bootstrap_health_service=expected)
        if name == "bioetl.composition.bootstrap.cli.config":
            return types.SimpleNamespace(bootstrap_config_service=expected)
        if name == "bioetl.composition.bootstrap.cli.noop":
            return types.SimpleNamespace(create_noop_logger=expected)
        raise AssertionError(f"Unexpected module import request: {name}")

    monkeypatch.setattr(cli_pkg, "import_module", _fake_import_module)

    assert cli_pkg.bootstrap_health_service is expected
    assert cli_pkg.bootstrap_config_service is expected
    assert cli_pkg.create_noop_logger is expected
    assert loader_calls == [
        "bioetl.composition.bootstrap.cli.health",
        "bioetl.composition.bootstrap.cli.config",
        "bioetl.composition.bootstrap.cli.noop",
    ]


@pytest.mark.unit
def test_lazy_export_raises_attribute_error_for_unknown_name() -> None:
    """Unknown symbol access in ``__getattr__`` must fail with AttributeError."""
    import bioetl.composition.bootstrap.cli as cli_pkg

    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(cli_pkg, "does_not_exist_in_cli_exports")
