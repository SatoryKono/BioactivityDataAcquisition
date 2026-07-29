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
"""Unit tests for storage audit wiring helper."""

from __future__ import annotations

from tests.helpers.synthetic_paths import synthetic_test_root
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.storage.audit import create_audit_port
from bioetl.domain.ports.noop import NoOpAudit
from bioetl.infrastructure.audit.file_audit import FileAuditAdapter

TEST_ROOT = synthetic_test_root("bioetl-audit-factory")
DATA_ROOT = TEST_ROOT / "bioetl"
CUSTOM_AUDIT_ROOT = TEST_ROOT / "custom-audit"


def _make_settings(
    *,
    audit_enabled: bool,
    audit_base_path: Path | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        data_dir=DATA_ROOT,
        observability=SimpleNamespace(
            audit_enabled=audit_enabled,
            audit_base_path=audit_base_path,
        ),
    )


@pytest.mark.unit
def test_create_audit_port_returns_noop_when_disabled() -> None:
    """Disabled audit returns explicit NoOpAudit rather than None."""
    settings = _make_settings(audit_enabled=False, audit_base_path=None)

    result = create_audit_port(settings=settings, logger=MagicMock())

    assert isinstance(result, NoOpAudit)


@pytest.mark.unit
def test_create_audit_port_returns_file_adapter_when_enabled() -> None:
    """Enabled audit returns FileAuditAdapter with configured path."""
    base_path = CUSTOM_AUDIT_ROOT
    settings = _make_settings(audit_enabled=True, audit_base_path=base_path)
    logger = MagicMock()
    metrics = MagicMock()
    tracing = MagicMock()

    result = create_audit_port(
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
    )

    assert isinstance(result, FileAuditAdapter)
    assert result.base_path == base_path
    assert result.logger is logger
    assert result.metrics is metrics
    assert result.tracing is tracing


@pytest.mark.unit
def test_create_audit_port_uses_default_output_audit_path() -> None:
    """Enabled audit without override uses data/output/audit."""
    settings = _make_settings(audit_enabled=True, audit_base_path=None)

    result = create_audit_port(settings=settings, logger=MagicMock())

    assert isinstance(result, FileAuditAdapter)
    assert result.base_path == DATA_ROOT / "output" / "audit"


@pytest.mark.unit
def test_create_audit_port_uses_noop_observability_when_ports_not_passed() -> None:
    """Audit factory should still construct a valid adapter without explicit ports."""
    settings = _make_settings(audit_enabled=True, audit_base_path=CUSTOM_AUDIT_ROOT)

    result = create_audit_port(settings=settings, logger=MagicMock())

    assert isinstance(result, FileAuditAdapter)
    assert result.metrics.__class__.__name__ == "NoOpMetrics"
    assert result.tracing.__class__.__name__ == "NoOpTracing"
