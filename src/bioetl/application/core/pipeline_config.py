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
    heartbeat_interval: int = 30
    wait_for_lock: bool = False
    lock_wait_timeout: int = 300
    lock_ttl: int | None = None

    def __post_init__(self) -> None:
        """Validate runtime config."""
        if self.limit is not None and self.limit <= 0:
            raise ValueError(f"limit must be positive or None, got {self.limit}")
        if self.heartbeat_interval <= 0:
            raise ValueError(
                f"heartbeat_interval must be positive, got {self.heartbeat_interval}"
            )
        if self.lock_wait_timeout <= 0:
            raise ValueError(
                f"lock_wait_timeout must be positive, got {self.lock_wait_timeout}"
            )

    @property
    def effective_lock_ttl(self) -> int:
        """Derived TTL for lock renewal based on runtime config."""

        return self.lock_ttl or self.heartbeat_interval * 3
