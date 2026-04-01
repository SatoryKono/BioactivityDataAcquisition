"""Canonical execution descriptor for a launched pipeline run.

This domain value object intentionally stays minimal and deterministic:
- immutable via ``frozen=True``
- no runtime-generated defaults
- no infrastructure or control-plane imports
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.types import RunType

__all__ = ["RunManifest"]


def _require_non_empty(value: str, field_name: str) -> str:
    """Return a normalized non-empty string or raise a domain-level error."""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Canonical immutable descriptor for pipeline execution."""

    run_id: str
    pipeline_name: str
    run_type: RunType
    config_hash: str
    contract_ref: str
    contract_version: str
    started_at: datetime

    def __post_init__(self) -> None:
        """Validate required fields without introducing non-determinism."""
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "pipeline_name",
            _require_non_empty(self.pipeline_name, "pipeline_name"),
        )
        object.__setattr__(
            self,
            "config_hash",
            _require_non_empty(self.config_hash, "config_hash"),
        )
        object.__setattr__(
            self,
            "contract_ref",
            _require_non_empty(self.contract_ref, "contract_ref"),
        )
        object.__setattr__(
            self,
            "contract_version",
            _require_non_empty(self.contract_version, "contract_version"),
        )

        if self.started_at.tzinfo is None:
            raise ValueError(
                "started_at must be timezone-aware; pass an explicit timestamp"
            )
