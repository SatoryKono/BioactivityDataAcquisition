"""Pipeline callback extraction and normalization service factory.

Extracted from builder.py to keep it within LOC limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext

if TYPE_CHECKING:
    from bioetl.application.core.wiring.runtime import (
        BasePipeline,
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.domain.behavior import DataNormalizationConfig
    from bioetl.domain.ports import DataNormalizationPort

__all__ = ["create_data_normalization_service", "extract_pipeline_callbacks"]


def extract_pipeline_callbacks(pipeline: BasePipeline) -> PipelineCallbacksContext:
    """Extract transformation callbacks from transformer or legacy methods.

    Returns:
        PipelineCallbacksContext with transform, gold filter, and gold transform callbacks.
    """
    transformer = pipeline.transformer
    if transformer is not None:
        transform_callback = cast(
            "TransformCallback",
            getattr(transformer, "transform_pre_silver", transformer.transform),
        )
        return PipelineCallbacksContext(
            transform=transform_callback,
            gold_filter=cast("GoldFilterCallback", transformer.should_write_gold),
            gold_transform=cast("GoldTransformCallback", transformer.transform_for_gold),
        )

    # Fallback for pipelines without explicit transformer (legacy)
    return PipelineCallbacksContext(
        transform=cast("TransformCallback", pipeline.transform_bronze_to_silver),
        gold_filter=cast(
            "GoldFilterCallback",
            getattr(pipeline, "should_write_gold", lambda _context, record: True),
        ),
        gold_transform=cast(
            "GoldTransformCallback",
            getattr(
                pipeline,
                "transform_for_gold",
                lambda _context, silver_record: silver_record,
            ),
        ),
    )


def create_data_normalization_service(
    config: DataNormalizationConfig | None = None,
) -> DataNormalizationPort:
    """Create the canonical data normalizer with optional configuration."""
    from bioetl.domain.behavior import (
        DataNormalizationConfig,
        DefaultDataNormalizer,
    )

    return DefaultDataNormalizer(config=config or DataNormalizationConfig())
