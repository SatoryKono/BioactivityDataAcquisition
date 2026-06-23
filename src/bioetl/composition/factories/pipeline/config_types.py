"""Type definitions for pipeline factory registry entries."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

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
