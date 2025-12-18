from typing import Any, NamedTuple, Optional, Type

import pyarrow as pa


class PipelineDefinition(NamedTuple):
    factory: Type[Any]
    silver_schema: Optional[pa.Schema]


class PipelineRegistry:
    _registry: dict[str, PipelineDefinition] = {}

    @classmethod
    def register(
        cls,
        pipeline_name: str,
        factory: Type[Any],
        silver_schema: Optional[pa.Schema] = None,
    ) -> None:
        cls._registry[pipeline_name] = PipelineDefinition(factory, silver_schema)

    @classmethod
    def get(cls, pipeline_name: str) -> PipelineDefinition:
        if pipeline_name not in cls._registry:
            raise ValueError(
                f"Unknown pipeline name: {pipeline_name}. Available: {list(cls._registry.keys())}"
            )
        return cls._registry[pipeline_name]

    @classmethod
    def list_pipelines(cls) -> list[str]:
        return list(cls._registry.keys())
