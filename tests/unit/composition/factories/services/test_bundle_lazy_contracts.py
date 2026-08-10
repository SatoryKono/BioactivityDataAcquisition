"""Behavioral contracts for lazy service-bundle compatibility seams."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.services import bundle
from bioetl.composition.factories.services._bundle_support import (
    BaseServicesFactoryProtocol,
)

pytestmark = pytest.mark.unit


def test_base_services_proxy_resolves_factory_for_each_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lazy proxy delegates metrics and service creation to the owner factory."""
    metrics = MagicMock(name="metrics")
    services = MagicMock(name="services")
    owner_factory = MagicMock(name="owner_factory")
    owner_factory._create_metrics.return_value = metrics
    owner_factory.create_common_services.return_value = services
    monkeypatch.setattr(
        "bioetl.composition.factories.services.factory.BaseServicesFactory",
        owner_factory,
    )
    proxy = bundle._BaseServicesFactoryProxy()
    settings = MagicMock(name="settings")

    assert proxy._create_metrics(settings) is metrics
    assert (
        proxy.create_common_services(
            settings=settings,
            logger=MagicMock(name="logger"),
            data_source=MagicMock(name="data_source"),
            pipeline_config=MagicMock(name="pipeline_config"),
            pipeline_name="chembl_activity",
        )
        is services
    )
    owner_factory._create_metrics.assert_called_once_with(settings)
    owner_factory.create_common_services.assert_called_once()


def test_load_pipeline_config_uses_canonical_direct_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public facade preserves the canonical loader result unchanged."""
    expected = MagicMock(name="pipeline_config")
    loader = MagicMock(return_value=expected)
    monkeypatch.setattr(bundle, "_load_pipeline_config_direct", loader)

    assert bundle.load_pipeline_config("chembl_activity") is expected
    loader.assert_called_once_with("chembl_activity")


def test_compute_config_hash_resolves_versioning_owner_lazily(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hash calculation resolves the versioning owner only at call time."""
    config = {"pipeline": "chembl_activity"}
    compute = MagicMock(return_value="sha256:contract")
    monkeypatch.setattr(
        "bioetl.composition.services.versioning.compute_config_hash",
        compute,
    )

    result = bundle.compute_config_hash(config)

    assert result == "sha256:contract"
    compute.assert_called_once_with(config)


def test_resolve_base_services_factory_honors_explicit_bundle_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicitly injected bundle-level factory remains the patch owner."""
    override = cast(BaseServicesFactoryProtocol, cast(Any, MagicMock()))
    monkeypatch.setattr(bundle, "BaseServicesFactory", override)

    assert bundle._resolve_base_services_factory() is override
