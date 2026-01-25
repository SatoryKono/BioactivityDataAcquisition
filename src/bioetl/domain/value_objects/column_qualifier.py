"""Column qualifier value object.

Handles column naming conventions for composite pipelines.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColumnQualifier:
    """Qualified column name: {provider}.{entity}.{field}."""

    provider: str
    entity: str
    field: str

    def __str__(self) -> str:
        return f"{self.provider}.{self.entity}.{self.field}"


def parse_pipeline_name(pipeline: str) -> tuple[str, str]:
    """Parse pipeline 'provider_entity' -> ('provider', 'entity').

    Args:
        pipeline: Pipeline name in format "provider_entity".

    Returns:
        Tuple of (provider, entity).

    Raises:
        ValueError: If pipeline name doesn't contain underscore separator.
    """
    if "_" not in pipeline:
        raise ValueError(
            f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
        )
    parts = pipeline.split("_", 1)
    return parts[0], parts[1]
