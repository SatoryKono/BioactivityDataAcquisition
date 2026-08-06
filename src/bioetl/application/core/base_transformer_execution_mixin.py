"""Execution lifecycle helpers shared by BaseTransformer."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bioetl.application.core._base_transformer_execution_support import (
    TransformerExecutionOwner,
    handle_transformation_error,
    handle_validation_error,
    record_metrics_and_close_span,
    start_transform_span,
)
from bioetl.application.core._base_transformer_structural_support import (
    apply_silver_filter,
    apply_structural_policy,
    evaluate_semantic_shadow_decision,
    record_structural_policy_metrics,
)
from bioetl.application.core.base_transformer.errors import (
    TransformationError,
)
from bioetl.application.core.base_transformer_helpers_mixin import (
    _BaseTransformerRecordHelpersMixin,
)
from bioetl.application.core.pipeline_span_lifecycle import _ClosableSpan

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import FilterDecision
    from bioetl.domain.types import BronzeRecord, SilverRecord


class _BaseTransformerExecutionMixin(_BaseTransformerRecordHelpersMixin):
    """Execution lifecycle helpers composed with record helpers (ARCH-REF-04)."""

    def _start_transform_span(
        self: TransformerExecutionOwner,
        context: PipelineContext,
        index: int,
    ) -> _ClosableSpan:
        """Create and enter an OpenTelemetry span for record transformation."""
        return start_transform_span(self, context, index)

    def _apply_silver_filter(
        self: TransformerExecutionOwner,
        context: PipelineContext,
        result: SilverRecord | None,
        index: int,
    ) -> None:
        """Check silver filter and raise FilteredOutError if excluded."""
        apply_silver_filter(self, context, result, index)

    def _evaluate_semantic_shadow_decision(
        self: TransformerExecutionOwner,
        result: SilverRecord | None,
    ) -> FilterDecision | None:
        """Evaluate structural Silver filters for shadow comparison only."""
        return evaluate_semantic_shadow_decision(self, result)

    def _record_structural_policy_metrics(
        self: TransformerExecutionOwner,
        *,
        action: str | None,
        shadow_comparison: str | None,
    ) -> None:
        """Emit bounded telemetry for structural actions and shadow comparisons."""
        record_structural_policy_metrics(
            self,
            action=action,
            shadow_comparison=shadow_comparison,
        )

    def _apply_structural_policy(
        self: TransformerExecutionOwner,
        context: PipelineContext,
        result: SilverRecord | None,
        index: int,
    ) -> SilverRecord | None:
        """Apply schema-aware structural policy before structural Silver filters."""
        return apply_structural_policy(self, context, result, index)

    def _handle_transformation_error(
        self: TransformerExecutionOwner,
        error: TransformationError,
        context: PipelineContext,
        span: _ClosableSpan,
    ) -> str:
        """Log and annotate span for transformation errors."""
        return handle_transformation_error(self, error, context, span)

    def _handle_validation_error(
        self: TransformerExecutionOwner,
        error: ValueError,
        context: PipelineContext,
        span: _ClosableSpan,
    ) -> str:
        """Log and annotate span for validation errors."""
        return handle_validation_error(self, error, context, span)

    def _record_metrics_and_close_span(
        self: TransformerExecutionOwner,
        start_time: float,
        error_type: str | None,
        span: _ClosableSpan,
    ) -> None:
        """Record transform duration/error metrics and close the OTEL span."""
        record_metrics_and_close_span(self, start_time, error_type, span)

    async def transform(
        self: TransformerExecutionOwner,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform Bronze record to Silver format (Template Method).

        Dispatches through instance hooks so subclasses can override policy,
        filter, error, and metrics seams (#7812). Structural policy evaluates
        and enforces Silver filters once for kept records (#7795).
        """
        start_time = time.perf_counter()
        error_type: str | None = None
        span = self._start_transform_span(context, index)

        try:
            result = await self._transform_impl(context, record, index)
            # Structural policy applies Silver filter once for non-quarantined
            # records; do not call _apply_silver_filter again after this.
            return self._apply_structural_policy(context, result, index)
        except TransformationError as error:
            error_type = self._handle_transformation_error(error, context, span)
            return None
        except ValueError as error:
            error_type = self._handle_validation_error(error, context, span)
            raise
        finally:
            self._record_metrics_and_close_span(start_time, error_type, span)
