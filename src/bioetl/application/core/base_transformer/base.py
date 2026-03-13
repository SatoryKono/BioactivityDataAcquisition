"""Base Transformer class for Bronze -> Silver transformations."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
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
from bioetl.domain.ports import (
    ContractPolicyPort,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldRecord

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.types import BronzeRecord, SilverRecord

__all__ = ["BaseTransformer", "T"]

_COMPAT_DEPENDENCY_BUILDER: Callable[[], TransformerDependencyContext] | None = None


def _merge_dependency_context(
    dependencies: TransformerDependencyContext,
    *,
    tracer: TracingPort | None,
    metrics: MetricsPort | None,
    identity_service: IdentityService | None,
    pii_hasher: PiiHasherPort | None,
    data_normalizer: DataNormalizationPort | None,
    contract_policy: ContractPolicyPort | None,
) -> TransformerDependencyContext:
    """Overlay explicit collaborators on top of a dependency context."""
    return TransformerDependencyContext(
        tracer=dependencies.tracer if tracer is None else tracer,
        metrics=dependencies.metrics if metrics is None else metrics,
        identity_service=(
            dependencies.identity_service
            if identity_service is None
            else identity_service
        ),
        pii_hasher=dependencies.pii_hasher if pii_hasher is None else pii_hasher,
        data_normalizer=(
            dependencies.data_normalizer
            if data_normalizer is None
            else data_normalizer
        ),
        contract_policy=(
            dependencies.contract_policy
            if contract_policy is None
            else contract_policy
        ),
    )


def _build_explicit_dependency_context(
    *,
    tracer: TracingPort | None,
    metrics: MetricsPort | None,
    identity_service: IdentityService | None,
    pii_hasher: PiiHasherPort | None,
    data_normalizer: DataNormalizationPort | None,
    contract_policy: ContractPolicyPort | None,
) -> TransformerDependencyContext:
    """Validate and materialize fully explicit collaborators."""
    explicit_values = {
        "tracer": tracer,
        "metrics": metrics,
        "identity_service": identity_service,
        "pii_hasher": pii_hasher,
        "data_normalizer": data_normalizer,
        "contract_policy": contract_policy,
    }
    missing = [name for name, value in explicit_values.items() if value is None]
    if missing:
        missing_list = ", ".join(missing)
        raise TypeError(
            "BaseTransformer requires explicit collaborator injection; "
            f"missing: {missing_list}. Build defaults in composition."
        )
    return TransformerDependencyContext(
        tracer=cast("TracingPort", tracer),
        metrics=cast("MetricsPort", metrics),
        identity_service=cast("IdentityService", identity_service),
        pii_hasher=cast("PiiHasherPort", pii_hasher),
        data_normalizer=cast("DataNormalizationPort", data_normalizer),
        contract_policy=cast("ContractPolicyPort", contract_policy),
    )


def _resolve_dependency_context(
    *,
    tracer: TracingPort | None,
    metrics: MetricsPort | None,
    identity_service: IdentityService | None,
    pii_hasher: PiiHasherPort | None,
    data_normalizer: DataNormalizationPort | None,
    contract_policy: ContractPolicyPort | None,
    dependencies: TransformerDependencyContext | None,
) -> TransformerDependencyContext:
    """Resolve transformer collaborators without constructing defaults locally."""
    if dependencies is not None:
        return _merge_dependency_context(
            dependencies,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
        )

    if _COMPAT_DEPENDENCY_BUILDER is not None and all(
        value is None
        for value in (
            tracer,
            metrics,
            identity_service,
            pii_hasher,
            data_normalizer,
            contract_policy,
        )
    ):
        return _COMPAT_DEPENDENCY_BUILDER()

    return _build_explicit_dependency_context(
        tracer=tracer,
        metrics=metrics,
        identity_service=identity_service,
        pii_hasher=pii_hasher,
        data_normalizer=data_normalizer,
        contract_policy=contract_policy,
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
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
        contract_policy: ContractPolicyPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> None:
        """Initialize transformer with explicitly wired collaborators."""
        self.provider = provider
        self.entity_type = entity_type or "unknown"
        self._silver_filters = silver_filters
        self._gold_filters = gold_filters
        resolved_dependencies = _resolve_dependency_context(
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
            dependencies=dependencies,
        )
        self._tracer = resolved_dependencies.tracer
        self._metrics = resolved_dependencies.metrics
        self._identity = resolved_dependencies.identity_service
        self._pii_hasher = resolved_dependencies.pii_hasher
        self._data_normalizer = resolved_dependencies.data_normalizer
        self._contract_policy = resolved_dependencies.contract_policy

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
        if result is not None and not self.should_write_silver(
            context,
            cast("GoldRecord", result),
        ):
            context.logger.debug(
                "silver_filter_excluded",
                provider=self.provider,
                entity_type=self.entity_type,
                record_index=index,
            )
            raise FilteredOutError()

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
