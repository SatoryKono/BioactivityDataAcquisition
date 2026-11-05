"""Deterministic normalization_profile_hash for composite preflight checks."""

from __future__ import annotations

import hashlib
from typing import Protocol


class _ProfileHashCarrier(Protocol):
    """Minimal profile contract needed to hash the composite DAG."""

    profile_hash: str


def get_expected_normalization_profile_hash(
    source_profiles: dict[str, _ProfileHashCarrier],
) -> str:
    """Compute the deterministic runtime normalization profile hash for the composite DAG."""
    if not source_profiles:
        return "empty_dag"
    components = [
        f"{source}:{profile.profile_hash}"
        for source, profile in sorted(source_profiles.items())
    ]
    return hashlib.sha256("|".join(components).encode("utf-8")).hexdigest()
