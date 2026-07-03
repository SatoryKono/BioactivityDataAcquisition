"""Additional branch coverage for tracing configuration helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.observability import tracing


pytestmark = pytest.mark.unit


def test_resolve_service_name_falls_back_to_constructor_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)

    assert tracing._resolve_service_name("bioetl-default") == "bioetl-default"


def test_non_local_otlp_endpoint_does_not_force_insecure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exporter_factory = MagicMock(return_value=object())
    monkeypatch.setattr(tracing, "OTLP_AVAILABLE", True)
    monkeypatch.setattr(tracing, "_OtlpExporterClass", exporter_factory)
    monkeypatch.setenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "https://otel.example.com:4317",
    )
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_INSECURE", raising=False)

    tracing._build_telemetry_exporter()

    exporter_factory.assert_called_once_with(
        endpoint="https://otel.example.com:4317",
    )
