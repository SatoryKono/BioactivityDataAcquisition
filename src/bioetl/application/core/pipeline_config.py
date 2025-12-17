"""Pipeline configuration - immutable data container.

Part of BasePipeline decomposition (ADR-0005).
Separates static configuration from runtime behavior.
"""

from dataclasses import dataclass

from bioetl.domain.types import RunType


@dataclass(frozen=True)
class PipelineRuntimeConfig:
    """Runtime execution parameters.

    Contains parameters that may vary between pipeline runs
    but are fixed during a single execution.
    """

    run_type: RunType
    resume: bool = False
    limit: int | None = None
    heartbeat_interval: float = 30.0
    """Interval in seconds for lock heartbeat."""

    def __post_init__(self) -> None:
        """Validate runtime config."""
        if self.limit is not None and self.limit <= 0:
            raise ValueError(f"limit must be positive or None, got {self.limit}")
