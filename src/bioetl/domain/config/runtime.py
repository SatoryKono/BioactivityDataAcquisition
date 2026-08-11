"""Runtime configuration object.

Defines the RuntimeConfig value object for CLI / runtime execution parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from bioetl.domain.types import RunType

__all__ = [
    "CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE",
    "LEGACY_SILVER_FILTER_COMPATIBILITY_MODE",
    "SILVER_FILTER_COMPATIBILITY_MODES",
    "RuntimeConfig",
    "SilverFilterCompatibilityMode",
]

HealthCheckMode = Literal["strict", "probe"]
SilverFilterCompatibilityMode = Literal[
    "structural_only_compat",
    "structural_only_auto_promote",
]
CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE: SilverFilterCompatibilityMode = (
    "structural_only_compat"
)
LEGACY_SILVER_FILTER_COMPATIBILITY_MODE: SilverFilterCompatibilityMode = (
    "structural_only_auto_promote"
)
SILVER_FILTER_COMPATIBILITY_MODES: frozenset[SilverFilterCompatibilityMode] = frozenset(
    {
        CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE,
        LEGACY_SILVER_FILTER_COMPATIBILITY_MODE,
    }
)


def _normalize_debug_export_formats(formats: tuple[str, ...]) -> tuple[str, ...]:
    valid_formats = {"csv", "xlsx"}
    normalized = tuple(str(fmt).strip().lower() for fmt in formats)
    invalid = [fmt for fmt in normalized if fmt not in valid_formats]
    if invalid:
        raise ValueError(
            f"debug_export_formats must contain only 'csv'/'xlsx', got {invalid!r}"
        )
    return normalized


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
    exact_replay: bool = False
    required_persistence_profile: str | None = None
    replay_anchor_date: str | None = None

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

    # Health-check enforcement mode for preflight.
    # strict: UNHEALTHY data_source blocks startup.
    # probe: network-related data_source health failures degrade to warning-level.
    health_check_mode: HealthCheckMode = "strict"

    # Skip Gold layer writing (composite sub-pipelines)
    # When True, Gold filter returns False for all records,
    # preventing individual Gold writes during composite execution
    skip_gold: bool = False
    debug_export_enabled: bool = False
    debug_export_formats: tuple[str, ...] = ()
    debug_export_dir: str | None = None
    workflow_id: str = "standalone"

    # Manual start offset for crash recovery (overrides checkpoint)
    # When set, extraction starts from this offset instead of checkpoint.
    # Requires run_type=incremental to avoid clearing already-loaded data.
    start_offset: int | None = None

    # Silver filter migration behavior captured for run-manifest identity.
    silver_filter_compatibility_mode: SilverFilterCompatibilityMode = (
        CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
    )

    def __post_init__(self) -> None:
        """Validate runtime config."""
        self._validate_positive_values()
        self._validate_lock_ttl()
        self._validate_health_check_mode()
        self._validate_replay_anchor_date()
        self._validate_silver_filter_compatibility_mode()
        self._validate_debug_export_formats()

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
            (
                self.lock_ttl is not None and self.lock_ttl <= 0,
                f"lock_ttl must be positive or None, got {self.lock_ttl}",
            ),
        ]
        for condition, message in validations:
            if condition:
                raise ValueError(message)

    def _validate_lock_ttl(self) -> None:
        if self.lock_ttl is not None and self.lock_ttl <= 0:
            raise ValueError(f"lock_ttl must be positive or None, got {self.lock_ttl}")

    def _validate_health_check_mode(self) -> None:
        """Validate health-check mode literal."""
        if self.health_check_mode not in {"strict", "probe"}:
            raise ValueError(
                "health_check_mode must be 'strict' or 'probe', "
                f"got {self.health_check_mode!r}"
            )

    def _validate_replay_anchor_date(self) -> None:
        """Validate the optional exact-replay date anchor."""
        if self.replay_anchor_date is None:
            return
        try:
            date.fromisoformat(self.replay_anchor_date)
        except ValueError as exc:
            raise ValueError(
                "replay_anchor_date must be an ISO date string (YYYY-MM-DD), "
                f"got {self.replay_anchor_date!r}"
            ) from exc

    def _validate_silver_filter_compatibility_mode(self) -> None:
        """Validate the Silver-filter migration compatibility mode."""
        if (
            self.silver_filter_compatibility_mode
            not in SILVER_FILTER_COMPATIBILITY_MODES
        ):
            raise ValueError(
                "silver_filter_compatibility_mode must be one of "
                f"{sorted(SILVER_FILTER_COMPATIBILITY_MODES)!r}, "
                f"got {self.silver_filter_compatibility_mode!r}"
            )

    def _validate_debug_export_formats(self) -> None:
        """Validate debug export format tokens."""
        normalized = _normalize_debug_export_formats(self.debug_export_formats)
        object.__setattr__(self, "debug_export_formats", normalized)

    @property
    def effective_lock_ttl(self) -> int:
        """Derived TTL for lock renewal based on runtime config."""
        # Fall back only when lock_ttl is unset (None), not when zero/negative
        # (those are rejected in _validate_positive_values).
        if self.lock_ttl is None:
            return self.heartbeat_interval * 3
        return self.lock_ttl
