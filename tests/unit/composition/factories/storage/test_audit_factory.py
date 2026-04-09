"""Unit tests for storage audit wiring helper."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.storage._audit import create_audit_port
from bioetl.domain.ports.noop import NoOpAudit
from bioetl.infrastructure.audit.file_audit import FileAuditAdapter


def _make_settings(
    *,
    audit_enabled: bool,
    audit_base_path: Path | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        data_dir=Path("/tmp/bioetl"),
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
    base_path = Path("/tmp/custom-audit")
    settings = _make_settings(audit_enabled=True, audit_base_path=base_path)
    logger = MagicMock()

    result = create_audit_port(settings=settings, logger=logger)

    assert isinstance(result, FileAuditAdapter)
    assert result.base_path == base_path
    assert result.logger is logger


@pytest.mark.unit
def test_create_audit_port_uses_default_output_audit_path() -> None:
    """Enabled audit without override uses data/output/audit."""
    settings = _make_settings(audit_enabled=True, audit_base_path=None)

    result = create_audit_port(settings=settings, logger=MagicMock())

    assert isinstance(result, FileAuditAdapter)
    assert result.base_path == Path("/tmp/bioetl/output/audit")
