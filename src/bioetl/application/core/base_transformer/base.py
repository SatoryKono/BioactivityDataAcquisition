"""Base Transformer class for Bronze -> Silver transformations."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bioetl.application.core.base_transformer.errors import (
    FilteredOutError,
    TransformationError,
)
from bioetl.application.core.base_transformer.types import (
    T,
    TransformerDependencyContext,
)
from bioetl.application.core.base_transformer_dependency_helpers_mixin import (
    _BaseTransformerDependencyHelpersMixin,
)
from bioetl.application.core.base_transformer_helpers_mixin import (
    _BaseTransformerRecordHelpersMixin,
)
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldRecord

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord

__all__ = ["BaseTransformer", "T"]


def _resolve_transformer_dependencies(
    *,
    dependencies: TransformerDependencyContext | None,
    tracer: TracingPort | None,
    metrics: MetricsPort | None,
    identity_service: IdentityService | None,
    pii_hasher: PiiHasherPort | None,
) -> TransformerDependencyContext:
    """Resolve explicit collaborator bundle for transformer construction."""
    if dependencies is not None:
        if any(
            collaborator is not None
            for collaborator in (tracer, metrics, identity_service, pii_hasher)
        ):
            raise TypeError(
                "Pass either 'dependencies' or named collaborators "
                "('tracer', 'metrics', 'identity_service', 'pii_hasher'), not both."
            )
        return dependencies

    if any(
        collaborator is not None
        for collaborator in (tracer, metrics, identity_service, pii_hasher)
    ):
        raise TypeError(
            "BaseTransformer no longer assembles partial collaborator defaults "
            "from named arguments. Build TransformerDependencyContext in "
            "composition or test support and pass it via 'dependencies'."
        )

    raise TypeError(
        "BaseTransformer requires explicit collaborator injection via "
        "'dependencies' (TransformerDependencyContext). Build runtime defaults "
        "in composition when needed."
    )


class BaseTransformer(
    _BaseTransformerDependencyHelpersMixin,
    _BaseTransformerRecordHelpersMixin,
    ABC,
):
    """Abstract base class for Bronze -> Silver transformers."""

    GOLD_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset()

    def __init__(
        self,
        provider: str,
        entity_type: str | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> None:
        """Initialize transformer with explicitly wired collaborators."""
        self.provider = provider
        self.entity_type = entity_type or "unknown"
        self._silver_filters = silver_filters
        self._gold_filters = gold_filters

        resolved_dependencies = _resolve_transformer_dependencies(
            dependencies=dependencies,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )

        self._tracer = resolved_dependencies.tracer
        self._metrics = resolved_dependencies.metrics
        self._identity = resolved_dependencies.identity_service
        self._pii_hasher = resolved_dependencies.pii_hasher
        self._data_normalizer = resolved_dependencies.data_normalizer
        self._contract_policy = resolved_dependencies.contract_policy
        self._structural_policy = resolved_dependencies.structural_policy

    def _start_transform_span(
        self,
        context: PipelineContext,
        index: int,
    ) -> Any:  # Any: OTel Span type varies by tracing backend
        """Create and enter an OpenTelemetry span for record transformation."""
        otel_tracer = self._tracer.get_tracer("bioetl.transformer")
        span = otel_tracer.start_as_current_span(
            "transform_record",
            attributes={
                "bioetl.provider": self.provider,
                "bioetl.entity_type": self.entity_type,
                "bioetl.run_id": str(context.run_id),
                "bioetl.record_index": index,
            },
        )
        span.__enter__()
        return span

    def _apply_silver_filter(
        self,
        context: PipelineContext,
        result: SilverRecord | None,
        index: int,
    ) -> None:
        """Check silver filter and raise FilteredOutError if excluded."""
        if result is None or self._silver_filters is None or self._silver_filters.is_empty():
            return

        decision = self._silver_filters.evaluate(cast("GoldRecord", result))
        if decision.include:
            return

        context.logger.debug(
            "silver_filter_quarantined",
            provider=self.provider,
            entity_type=self.entity_type,
            record_index=index,
            filter_reason_code=decision.reason_code,
            filter_rule_type=decision.rule_type,
            filter_field=decision.field,
        )
        raise FilteredOutError(
            decision.message or "Record excluded by silver filters",
            details=decision.to_dict(),
        )

    def _apply_structural_policy(
        self,
        context: PipelineContext,
        result: SilverRecord | None,
        index: int,
    ) -> SilverRecord | None:
        """Apply schema-aware structural policy before semantic Silver filters."""
        if result is None:
            return None

        outcome = self._structural_policy.apply(result)
        for event in outcome.events:
            log_method = getattr(context.logger, event.level)
            log_method(
                event.event,
                provider=self.provider,
                entity_type=self.entity_type,
                record_index=index,
                **event.details,
            )

        if not outcome.should_quarantine:
            return outcome.record

        details = outcome.details or {}
        context.logger.debug(
            "silver_structural_quarantined",
            provider=self.provider,
            entity_type=self.entity_type,
            record_index=index,
            reason_code=details.get("reason_code"),
            field=details.get("field"),
            action_taken=details.get("action_taken"),
        )
        raise FilteredOutError(
            outcome.quarantine_reason or "Record excluded by structural policy",
            details=details,
        )

    def _handle_transformation_error(
        self,
        error: TransformationError,
        context: PipelineContext,
        span: Any,  # Any: OTel Span type varies by tracing backend
    ) -> str:
        """Log and annotate span for transformation errors."""
        error_type = "transformation_error"
        context.logger.warning(
            "transformation_skipped",
            reason=str(error),
            field=error.field,
            provider=self.provider,
        )
        span.set_attribute("error", True)
        span.set_attribute("error.type", error_type)
        return error_type

    def _handle_validation_error(
        self,
        error: ValueError,
        context: PipelineContext,
        span: Any,  # Any: OTel Span type varies by tracing backend
    ) -> str:
        """Log and annotate span for validation errors."""
        error_type = "validation_error"
        context.logger.warning(
            "entity_validation_failed",
            error=str(error),
            provider=self.provider,
        )
        span.set_attribute("error", True)
        span.set_attribute("error.type", error_type)
        return error_type

    def _record_metrics_and_close_span(
        self,
        start_time: float,
        error_type: str | None,
        span: Any,  # Any: OTel Span type varies by tracing backend
    ) -> None:
        """Record transform duration/error metrics and close the OTEL span."""
        duration = time.perf_counter() - start_time
        self._metrics.observe_histogram(
            "transform_duration_seconds",
            duration,
            labels={
                "provider": self.provider,
                "entity_type": self.entity_type,
            },
        )
        if error_type:
            self._metrics.increment_counter(
                "transform_errors_total",
                1,
                labels={
                    "provider": self.provider,
                    "entity_type": self.entity_type,
                    "error_type": error_type,
                },
            )
        span.set_attribute("bioetl.duration_ms", duration * 1000)
        span.__exit__(None, None, None)

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
            result = await self._transform_impl(context, record, index)
            result = self._apply_structural_policy(context, result, index)
            self._apply_silver_filter(context, result, index)
            return result
        except TransformationError as e:
            error_type = self._handle_transformation_error(e, context, span)
            return None
        except ValueError as e:
            error_type = self._handle_validation_error(e, context, span)
            return None
        finally:
            self._record_metrics_and_close_span(start_time, error_type, span)

    @abstractmethod
    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Implement entity-specific transformation logic."""
        ...

    def should_write_silver(
        self,
        _context: PipelineContext,
        record: GoldRecord,
    ) -> bool:
        """Determine whether transformed record should be written to Silver."""
        if self._silver_filters is None or self._silver_filters.is_empty():
            return True
        return self._silver_filters.should_include(record)

    def should_write_gold(
        self,
        _context: PipelineContext,
        record: GoldRecord,
    ) -> bool:
        """Determine whether transformed record should be written to Gold."""
        if self._gold_filters is None or self._gold_filters.is_empty():
            return True
        return self._gold_filters.should_include(record)
