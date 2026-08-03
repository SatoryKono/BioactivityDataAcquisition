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
"""Focused tests for postrun collaborator resolution helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.postrun._service_collaborators import (
    resolve_postrun_collaborators,
)


pytestmark = pytest.mark.unit


def test_resolve_postrun_collaborators_reads_collaborators_from_services() -> None:
    """Collaborators should be sourced from the canonical services bundle."""
    context = MagicMock()
    context.logger = MagicMock()
    services = MagicMock()
    services.storage = MagicMock(name="services_storage")
    services.metrics = MagicMock(name="services_metrics")
    services.logger = MagicMock(name="services_logger")
    services.metadata_coordinator = MagicMock(name="services_metadata_coordinator")
    services.metadata_writer = MagicMock(name="services_metadata_writer")

    resolved = resolve_postrun_collaborators(
        services=services,
        context=context,
    )

    assert resolved.storage is services.storage
    assert resolved.logger is services.logger
    assert resolved.metrics is services.metrics
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


def test_resolve_postrun_collaborators_rejects_missing_services() -> None:
    """Services bundle is mandatory after removing legacy constructor kwargs."""
    context = MagicMock()
    context.logger = MagicMock(name="context_logger")

    with pytest.raises(AssertionError, match="requires services"):
        resolve_postrun_collaborators(
            services=None,
            context=context,
        )
