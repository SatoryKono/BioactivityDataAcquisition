"""Legacy-only compatibility fingerprints for degraded runtime anchors."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.normalization.fingerprints import (
    compute_execution_identity_fingerprint,
)

__all__ = ["compute_degraded_runtime_anchor_fingerprint"]


def compute_degraded_runtime_anchor_fingerprint(
    payload: Mapping[str, object | None],
) -> str:
    """Compute the explicitly degraded runtime-anchor compatibility fingerprint.

    This helper is intentionally outside the canonical fingerprint namespace. It
    exists only for legacy checkpoint compatibility paths when a full execution
    fingerprint or canonical checkpoint-execution payload is unavailable.
    """

    return compute_execution_identity_fingerprint(payload)
