"""Base Transformer class for Bronze -> Silver transformations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar

from bioetl.application.core.base_transformer.types import (
    T,
    TransformerDependencyContext,
)
from bioetl.application.core.base_transformer_dependency_helpers_mixin import (
    _BaseTransformerDependencyHelpersMixin,
)
from bioetl.application.core.base_transformer_execution_mixin import (
    _BaseTransformerExecutionMixin,
)
from bioetl.application.core.base_transformer_helpers_mixin import (
    _BaseTransformerRecordHelpersMixin,
)
from bioetl.domain.behavior import EntityIdentityGenerator
from bioetl.domain.context import PipelineContext

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, GoldRecord, SilverRecord

__all__ = ["BaseTransformer", "T"]


def _resolve_transformer_dependencies(
    *,
    dependencies: TransformerDependencyContext | None,
    tracer: TracingPort | None,
    metrics: MetricsPort | None,
    identity_service: EntityIdentityGenerator | None,
    pii_hasher: PiiHasherPort | None,
) -> TransformerDependencyContext:
    """Resolve explicit collaborator bundle for transformer construction."""
    if dependencies is not None:
        if any(
            collaborator is not None
            for collaborator in (tracer, metrics, identity_service, pii_hasher)
        ):
            return replace(
                dependencies,
                tracer=dependencies.tracer if tracer is None else tracer,
                metrics=dependencies.metrics if metrics is None else metrics,
                identity_service=(
                    dependencies.identity_service
                    if identity_service is None
                    else identity_service
                ),
                pii_hasher=(
                    dependencies.pii_hasher if pii_hasher is None else pii_hasher
                ),
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
    _BaseTransformerExecutionMixin,
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
        identity_service: EntityIdentityGenerator | None = None,
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
        should_include: bool = self._silver_filters.should_include(record)
        return should_include

    def should_write_gold(
        self,
        _context: PipelineContext,
        record: GoldRecord,
    ) -> bool:
        """Determine whether transformed record should be written to Gold."""
        if self._gold_filters is None or self._gold_filters.is_empty():
            return True
        should_include: bool = self._gold_filters.should_include(record)
        return should_include
