"""Focused tests for postrun collaborator resolution helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.postrun._service_collaborators import (
    resolve_postrun_collaborators,
)


pytestmark = pytest.mark.unit


def test_resolve_postrun_collaborators_prefers_explicit_values() -> None:
    """Explicit collaborators should override service-container collaborators."""
    context = MagicMock()
    context.logger = MagicMock()
    services = MagicMock()
    services.storage = MagicMock(name="services_storage")
    services.metrics = MagicMock(name="services_metrics")
    services.logger = MagicMock(name="services_logger")
    services.metadata_coordinator = MagicMock(name="services_metadata_coordinator")
    services.metadata_writer = MagicMock(name="services_metadata_writer")

    explicit_storage = MagicMock(name="explicit_storage")
    explicit_logger = MagicMock(name="explicit_logger")
    explicit_metrics = MagicMock(name="explicit_metrics")

    resolved = resolve_postrun_collaborators(
        services=services,
        context=context,
        storage=explicit_storage,
        logger=explicit_logger,
        metrics=explicit_metrics,
    )

    assert resolved.storage is explicit_storage
    assert resolved.logger is explicit_logger
    assert resolved.metrics is explicit_metrics
    assert resolved.metadata_coordinator is services.metadata_coordinator
    assert resolved.metadata_writer is services.metadata_writer


def test_resolve_postrun_collaborators_defaults_logger_only() -> None:
    """Context logger should fill absent logger collaborator."""
    context = MagicMock()
    context.logger = MagicMock(name="context_logger")
    services = MagicMock()
    services.storage = MagicMock(name="services_storage")
    services.metrics = MagicMock(name="services_metrics")
    services.logger = None
    services.metadata_coordinator = None
    services.metadata_writer = None

    resolved = resolve_postrun_collaborators(
        services=services,
        context=context,
    )

    assert resolved.storage is services.storage
    assert resolved.logger is context.logger
    assert resolved.metrics is services.metrics
    assert resolved.metadata_coordinator is None
    assert resolved.metadata_writer is None


def test_resolve_postrun_collaborators_rejects_missing_metrics() -> None:
    """Metrics must be provided explicitly or via services."""
    context = MagicMock()
    context.logger = MagicMock(name="context_logger")
    services = MagicMock()
    services.storage = MagicMock(name="services_storage")
    services.metrics = None
    services.logger = None
    services.metadata_coordinator = None
    services.metadata_writer = None

    with pytest.raises(AssertionError, match="requires metrics"):
        resolve_postrun_collaborators(
            services=services,
            context=context,
        )
