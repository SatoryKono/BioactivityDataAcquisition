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
        if not self.pipeline_name:
            raise ValueError("pipeline_name cannot be empty")
        if not self.provider:
            raise ValueError("provider cannot be empty")
        if not self.entity_type:
            raise ValueError("entity_type cannot be empty")
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {self.batch_size}")
        if self.checkpoint_interval <= 0:
            raise ValueError(
                f"checkpoint_interval must be positive, got {self.checkpoint_interval}"
            )
        if not self.primary_keys:
            raise ValueError("primary_keys cannot be empty")

    @property
    def lock_key(self) -> str:
        """Generate lock key for distributed locking."""
        return f"pipeline:{self.pipeline_name}"
