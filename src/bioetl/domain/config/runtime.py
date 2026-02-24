"""Runtime configuration object.

Defines the RuntimeConfig value object for CLI / runtime execution parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import RunType


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Runtime execution parameters.

    Contains parameters that may vary between pipeline runs
    but are fixed during a single execution. These are typically
    passed via CLI arguments.

    This is a Value Object that belongs in the domain layer because
    it has no I/O dependencies and represents immutable runtime state.
    """

    run_type: RunType
    resume: bool = False
    limit: int | None = None
    heartbeat_interval: int = 30
    wait_for_lock: bool = False
    lock_wait_timeout: int = 300
    lock_ttl: int | None = 90
    query: str | None = None
    dry_run: bool = False

    # VACUUM automation (Phase 1 refactoring)
    # When enabled, VACUUM is executed after successful pipeline run
    vacuum_after_run: bool = False
    vacuum_retention_days: int = 7

    # Storage optimization (Unifies cleanup policies)
    # Controls explicit storage maintenance (vacuum, old file removal)
    optimize_storage: bool = False

    # Medallion invariants validation (REQ-CONF-001)
    # When True, Medallion config violations fail the pipeline
    # When False, violations are logged as warnings
    strict_validation: bool = False

    # Gold layer schema validation (strict mode)
    # When True, pipelines fail if Gold schema is not provided
    # Default True to enforce strict Gold validation (override only in non-prod)
    strict_gold_validation: bool = True

    # Skip Gold layer writing (composite sub-pipelines)
    # When True, Gold filter returns False for all records,
    # preventing individual Gold writes during composite execution
    skip_gold: bool = False

    # Manual start offset for crash recovery (overrides checkpoint)
    # When set, extraction starts from this offset instead of checkpoint.
    # Requires run_type=incremental to avoid clearing already-loaded data.
    start_offset: int | None = None

    def __post_init__(self) -> None:
        """Validate runtime config."""
        self._validate_positive_values()

    def _validate_positive_values(self) -> None:
        """Validate that numeric fields have positive values."""
        validations = [
            (
                self.limit is not None and self.limit <= 0,
                f"limit must be positive or None, got {self.limit}",
            ),
            (
                self.heartbeat_interval <= 0,
                f"heartbeat_interval must be positive, got {self.heartbeat_interval}",
            ),
            (
                self.lock_wait_timeout <= 0,
                f"lock_wait_timeout must be positive, got {self.lock_wait_timeout}",
            ),
            (
                self.vacuum_retention_days <= 0,
                f"vacuum_retention_days must be positive, got {self.vacuum_retention_days}",
            ),
            (
                self.start_offset is not None and self.start_offset < 0,
                f"start_offset must be non-negative or None, got {self.start_offset}",
            ),
        ]
        for condition, message in validations:
            if condition:
                raise ValueError(message)

    @property
    def effective_lock_ttl(self) -> int:
        """Derived TTL for lock renewal based on runtime config."""
        return self.lock_ttl or self.heartbeat_interval * 3
