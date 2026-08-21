# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Health CLI must rehydrate provider-health gauges through composition."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_observability as observability,
)


pytestmark = pytest.mark.unit


def test_rehydrate_provider_health_gauges_uses_composition_seam() -> None:
    deps = SimpleNamespace(metrics=MagicMock(name="MetricsPort"))

    with patch(
        "bioetl.composition.health_service_access.rehydrate_provider_health_gauges",
        return_value=1,
    ) as rehydrate:
        observability._rehydrate_provider_health_gauges(deps)

    rehydrate.assert_called_once_with(deps.metrics)


def test_rehydrate_provider_health_gauges_swallows_runtime_errors() -> None:
    deps = SimpleNamespace(metrics=MagicMock(name="MetricsPort"))

    with patch(
        "bioetl.composition.health_service_access.rehydrate_provider_health_gauges",
        side_effect=RuntimeError("store unavailable"),
    ):
        observability._rehydrate_provider_health_gauges(deps)


def test_health_observability_module_does_not_import_infrastructure() -> None:
    source = observability.__file__
    assert source is not None
    text = Path(source).read_text(encoding="utf-8")
    assert "bioetl.infrastructure" not in text
