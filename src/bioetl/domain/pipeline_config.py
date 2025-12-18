"""Pipeline configuration - immutable data container.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable pipeline configuration.

    Contains static configuration that doesn't change during execution.
    Frozen dataclass ensures immutability after creation.
    """

    pipeline_name: str
    provider: str
    entity_type: str
    primary_keys: list[str]
    silver_table: str
    gold_table: str | None = None
    batch_size: int = 100
    checkpoint_interval: int = 1000
    fields: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        # Data-driven validation to reduce cyclomatic complexity
        validations = [
            (not self.pipeline_name, "pipeline_name cannot be empty"),
            (not self.provider, "provider cannot be empty"),
            (not self.entity_type, "entity_type cannot be empty"),
            (self.batch_size <= 0, f"batch_size must be positive, got {self.batch_size}"),
            (
                self.checkpoint_interval <= 0,
                f"checkpoint_interval must be positive, got {self.checkpoint_interval}",
            ),
            (not self.primary_keys, "primary_keys cannot be empty"),
        ]
        for condition, message in validations:
            if condition:
                raise ValueError(message)

    @property
    def lock_key(self) -> str:
        """Generate lock key for distributed locking."""
        return f"pipeline:{self.pipeline_name}"
