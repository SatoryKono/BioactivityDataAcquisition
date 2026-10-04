"""Type definitions for pipeline factory registry entries."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple, Self

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base_transformer import BaseTransformer


type TransformerClassRef = "type[BaseTransformer] | str"

__all__ = ["PipelineFactoryConfig", "TransformerClassRef"]


class PipelineFactoryConfig(NamedTuple):
    """Value object describing one pipeline factory registration."""

    pipeline_name: str
    provider: str
    entity_type: str
    transformer_class: TransformerClassRef
    silver_schema: pa.Schema | None
    gold_schema: object
    pandera_silver_schema: object | None = None
    data_source_provider: str | None = None

    @classmethod
    def for_pipeline(
        cls,
        pipeline_name: str,
        *,
        transformer_class: TransformerClassRef,
        silver_schema: pa.Schema | None,
        gold_schema: object,
        pandera_silver_schema: object | None = None,
        data_source_provider: str | None = None,
    ) -> Self:
        """Bind explicit schemas to the canonical provider_entity identity."""
        provider, separator, entity = pipeline_name.partition("_")
        if not provider or not separator or not entity:
            raise ValueError("pipeline_name must contain provider and entity")
        return cls(
            pipeline_name,
            provider,
            entity,
            transformer_class,
            silver_schema,
            gold_schema,
            pandera_silver_schema,
            data_source_provider,
        )
