"""Contract tests for lazy package exports covered by issue #10469."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

import bioetl.application.composite as application_composite
import bioetl.composition.bootstrap as composition_bootstrap
import bioetl.infrastructure.observability as infrastructure_observability

pytestmark = pytest.mark.unit


def test_application_composite_resolves_caches_and_lists_lazy_export() -> None:
    sentinel = object()
    export_name = "CoverageSentinel"
    application_composite._EXPORTS[export_name] = ("coverage.module", "sentinel")
    application_composite.__dict__.pop(export_name, None)
    try:
        with patch.object(
            application_composite,
            "import_module",
            return_value=SimpleNamespace(sentinel=sentinel),
        ) as importer:
            assert application_composite.__getattr__(export_name) is sentinel
        importer.assert_called_once_with("coverage.module")
        assert application_composite.__dict__[export_name] is sentinel
        assert "CompositePipelineRunner" in application_composite.__dir__()
        with pytest.raises(AttributeError, match="does_not_exist"):
            application_composite.__getattr__("does_not_exist")
    finally:
        application_composite._EXPORTS.pop(export_name, None)
        application_composite.__dict__.pop(export_name, None)


def test_composition_bootstrap_resolves_runtime_module_and_lists_exports() -> None:
    sentinel = object()
    composition_bootstrap.__dict__.pop("runtime", None)
    try:
        with patch.object(
            composition_bootstrap, "import_module", return_value=sentinel
        ) as importer:
            assert composition_bootstrap.__getattr__("runtime") is sentinel
        importer.assert_called_once_with("bioetl.composition.bootstrap.runtime")
        assert composition_bootstrap.__dict__["runtime"] is sentinel
        assert "bootstrap_pipeline_runner" in composition_bootstrap.__dir__()
    finally:
        composition_bootstrap.__dict__.pop("runtime", None)


def test_infrastructure_observability_resolves_caches_and_lists_lazy_export() -> None:
    sentinel = object()
    export_name = "CoverageSentinel"
    infrastructure_observability._EXPORT_MAP[export_name] = (
        "coverage.module",
        "sentinel",
    )
    infrastructure_observability.__dict__.pop(export_name, None)
    try:
        with patch.object(
            infrastructure_observability,
            "import_module",
            return_value=SimpleNamespace(sentinel=sentinel),
        ) as importer:
            assert infrastructure_observability.__getattr__(export_name) is sentinel
        importer.assert_called_once_with("coverage.module")
        assert infrastructure_observability.__dict__[export_name] is sentinel
        assert "PrometheusMetrics" in infrastructure_observability.__dir__()
    finally:
        infrastructure_observability._EXPORT_MAP.pop(export_name, None)
        infrastructure_observability.__dict__.pop(export_name, None)
