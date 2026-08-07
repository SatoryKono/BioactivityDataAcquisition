"""Cross-validation configuration models for composite pipelines."""

from __future__ import annotations

import math
from dataclasses import dataclass

from bioetl.domain.composite.config_validators import (
    _coerce_to_typed_tuple,
)
from bioetl.domain.composite.cross_validation import EnricherFieldPairing


def _require_finite_number(value: float | int, name: str) -> None:
    """Reject non-numeric and non-finite threshold/tolerance inputs."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")


def _validate_cross_validation_thresholds(
    warning_threshold: int,
    error_threshold: int,
    quarantine_threshold: int,
) -> None:
    _require_finite_number(warning_threshold, "warning_threshold")
    _require_finite_number(error_threshold, "error_threshold")
    _require_finite_number(quarantine_threshold, "quarantine_threshold")
    if warning_threshold < 1:
        raise ValueError(f"warning_threshold must be >= 1, got {warning_threshold}")
    if error_threshold < 2:
        raise ValueError(f"error_threshold must be >= 2, got {error_threshold}")
    if warning_threshold >= error_threshold:
        raise ValueError("warning_threshold must be < error_threshold")
    if quarantine_threshold < 1:
        raise ValueError(
            f"quarantine_threshold must be >= 1, got {quarantine_threshold}"
        )


def _validate_cross_validation_tolerances(
    fuzzy_threshold: float,
    numeric_tolerance: float,
) -> None:
    _require_finite_number(fuzzy_threshold, "fuzzy_threshold")
    _require_finite_number(numeric_tolerance, "numeric_tolerance")
    if not 0.0 < fuzzy_threshold <= 1.0:
        raise ValueError(
            f"fuzzy_threshold must be in (0.0, 1.0], got {fuzzy_threshold}"
        )
    if not 0.0 < numeric_tolerance <= 1.0:
        raise ValueError(
            f"numeric_tolerance must be in (0.0, 1.0], got {numeric_tolerance}"
        )


@dataclass(frozen=True, slots=True)
class CrossValidationConfig:
    """Configuration for cross-enricher data validation."""

    enabled: bool = True
    warning_threshold: int = 1
    error_threshold: int = 2
    quarantine_threshold: int = 2
    fuzzy_threshold: float = 0.8
    numeric_tolerance: float = 0.10
    enricher_pairings: tuple[EnricherFieldPairing, ...] = ()

    def __post_init__(self) -> None:
        _coerce_to_typed_tuple(self, "enricher_pairings", EnricherFieldPairing)
        self._validate()

    def _validate(self) -> None:
        _validate_cross_validation_thresholds(
            self.warning_threshold,
            self.error_threshold,
            self.quarantine_threshold,
        )
        _validate_cross_validation_tolerances(
            self.fuzzy_threshold,
            self.numeric_tolerance,
        )

    def get_pairing(self, enricher_pipeline: str) -> EnricherFieldPairing | None:
        """Look up field pairing config for the given enricher pipeline."""
        for pairing in self.enricher_pairings:
            if pairing.enricher_pipeline == enricher_pipeline:
                return pairing
        return None


__all__ = ["CrossValidationConfig"]
