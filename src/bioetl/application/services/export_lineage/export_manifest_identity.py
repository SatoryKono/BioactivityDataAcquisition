"""Identity and timestamp helpers for export sidecar manifests.

Pure identity functions live in ``bioetl.domain.value_objects.export_identity``
(ARCH-REF-R2 / #7732). Clock-bound resolution remains application-owned.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.runtime_clock import RuntimeClock
from bioetl.domain.value_objects.export_identity import (
    dataset_bundle_id,
    fingerprint_payload,
    format_utc,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort

__all__ = [
    "dataset_bundle_id",
    "fingerprint_payload",
    "format_utc",
    "resolve_generated_at",
    "utc_now",
]


def resolve_generated_at(
    generated_at: str | None,
    *,
    allow_nondeterministic: bool,
    clock: ClockPort | None,
) -> str:
    """Resolve export manifest timestamp without implicit wall-clock drift.

    Deterministic path (default): requires an explicit ``generated_at``.
    Operator opt-in path: uses injected ``ClockPort`` only (never raw
    ``datetime.now``). When opt-in is set without a clock, ``RuntimeClock``
    is used as the sole classified wall-clock adapter seam.
    """
    if generated_at is not None:
        timestamp = generated_at.strip()
        if timestamp:
            return timestamp
    if allow_nondeterministic:
        resolved_clock = clock if clock is not None else RuntimeClock()
        return format_utc(resolved_clock.now())
    raise ValueError(
        "generated_at must be provided for deterministic export manifests; "
        "operator-only exports must opt into non-deterministic generated_at"
    )


def utc_now() -> str:
    """Return the current UTC time via the RuntimeClock adapter seam.

    Operator-only helper. Prefer :func:`resolve_generated_at` with an injected
    ``ClockPort`` for identity-bearing timestamps.
    """
    return format_utc(RuntimeClock().now())
