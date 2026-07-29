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
"""Unit tests for dependency progress service."""

from __future__ import annotations

import pytest

from unittest.mock import MagicMock

from bioetl.application.composite.dependency_progress_tracker import (
    DependencyProgressService,
)
from bioetl.domain.composite.config import DependencyConfig
from bioetl.domain.composite.result import DependencyResult, DependencyStatus


pytestmark = pytest.mark.unit


def _make_logger() -> MagicMock:
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.error = MagicMock()
    return logger


def test_maybe_store_completed_skip_records_skipped_result() -> None:
    """Completed dependency should be materialized as skipped result."""
    tracker = DependencyProgressService(_make_logger())
    dependency = DependencyConfig(
        pipeline="chembl_publication_term",
        join_keys=("document_chembl_id",),
    )
    results: dict[str, DependencyResult] = {}

    handled = tracker.maybe_store_completed_skip(
        dependency=dependency,
        completed=frozenset({dependency.pipeline}),
        results=results,
    )

    assert handled is True
    assert results[dependency.pipeline].status == DependencyStatus.SKIPPED


def test_should_stop_after_result_true_for_required_failure() -> None:
    """Required failed dependency should stop sequential execution."""
    logger = _make_logger()
    tracker = DependencyProgressService(logger)
    dependency = DependencyConfig(
        pipeline="chembl_publication_term",
        join_keys=("document_chembl_id",),
        required=True,
    )

    should_stop = tracker.should_stop_after_result(
        dependency=dependency,
        result=DependencyResult.failed(dependency.pipeline, "failed"),
    )

    assert should_stop is True
    logger.error.assert_called_once()


def test_should_stop_after_result_false_for_optional_failure() -> None:
    """Optional dependency failure should not stop execution."""
    tracker = DependencyProgressService(_make_logger())
    dependency = DependencyConfig(
        pipeline="chembl_publication_term",
        join_keys=("document_chembl_id",),
        required=False,
    )

    should_stop = tracker.should_stop_after_result(
        dependency=dependency,
        result=DependencyResult.failed(dependency.pipeline, "failed"),
    )

    assert should_stop is False
