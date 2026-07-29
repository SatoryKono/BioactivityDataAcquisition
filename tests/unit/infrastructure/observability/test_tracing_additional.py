# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
    monkeypatch.setattr(tracing, "otlp_available", True)
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
