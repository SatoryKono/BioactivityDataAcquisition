"""Execution lifecycle helpers shared by BaseTransformer."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core._base_transformer_execution_support import (
    TransformerExecutionOwner,
    apply_silver_filter,
    apply_structural_policy,
    handle_transformation_error,
    handle_validation_error,
    record_metrics_and_close_span,
    record_structural_policy_metrics,
    start_transform_span,
)
from bioetl.application.core.base_transformer.errors import (
    TransformationError,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import FilterDecision
    from bioetl.domain.types import BronzeRecord, SilverRecord


class _BaseTransformerExecutionMixin:
    """Execution lifecycle helpers delegated from BaseTransformer."""

    def _start_transform_span(
        self,
        context: PipelineContext,
        index: int,
    ) -> Any:
        """Create and enter an OpenTelemetry span for record transformation."""
        return start_transform_span(cast("TransformerExecutionOwner", self), context, index)

    def _apply_silver_filter(
        self,
        context: PipelineContext,
        result: SilverRecord | None,
        index: int,
    ) -> None:
        """Check silver filter and raise FilteredOutError if excluded."""
        apply_silver_filter(cast("TransformerExecutionOwner", self), context, result, index)

    def _evaluate_semantic_shadow_decision(
        self,
        result: SilverRecord | None,
    ) -> FilterDecision | None:
        """Evaluate semantic Silver filters for shadow comparison only."""
        owner = cast("TransformerExecutionOwner", self)
        if result is None or owner._silver_filters is None or owner._silver_filters.is_empty():
            return None
        return owner._silver_filters.evaluate(cast("dict[str, object]", result))

    def _record_structural_policy_metrics(
        self,
        *,
        action: str | None,
        shadow_comparison: str | None,
    ) -> None:
        """Emit bounded telemetry for structural actions and shadow comparisons."""
        record_structural_policy_metrics(
            cast("TransformerExecutionOwner", self),
            action=action,
            shadow_comparison=shadow_comparison,
        )

    def _apply_structural_policy(
        self,
        context: PipelineContext,
        result: SilverRecord | None,
        index: int,
    ) -> SilverRecord | None:
        """Apply schema-aware structural policy before semantic Silver filters."""
        return apply_structural_policy(
            cast("TransformerExecutionOwner", self),
            context,
            result,
            index,
        )

    def _handle_transformation_error(
        self,
        error: TransformationError,
        context: PipelineContext,
        span: Any,
    ) -> str:
        """Log and annotate span for transformation errors."""
        return handle_transformation_error(
            cast("TransformerExecutionOwner", self),
            error,
            context,
            span,
        )

    def _handle_validation_error(
        self,
        error: ValueError,
        context: PipelineContext,
        span: Any,
    ) -> str:
        """Log and annotate span for validation errors."""
        return handle_validation_error(
            cast("TransformerExecutionOwner", self),
            error,
            context,
            span,
        )

    def _record_metrics_and_close_span(
        self,
        start_time: float,
        error_type: str | None,
        span: Any,
    ) -> None:
        """Record transform duration/error metrics and close the OTEL span."""
        record_metrics_and_close_span(
            cast("TransformerExecutionOwner", self),
            start_time,
            error_type,
            span,
        )

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform Bronze record to Silver format (Template Method)."""
        start_time = time.perf_counter()
        error_type: str | None = None
        span = self._start_transform_span(context, index)

        try:
            owner = cast("TransformerExecutionOwner", self)
            result = await owner._transform_impl(context, record, index)
            result = self._apply_structural_policy(context, result, index)
            self._apply_silver_filter(context, result, index)
            return result
        except TransformationError as error:
            error_type = self._handle_transformation_error(error, context, span)
            return None
        except ValueError as error:
            error_type = self._handle_validation_error(error, context, span)
            return None
        finally:
            self._record_metrics_and_close_span(start_time, error_type, span)
