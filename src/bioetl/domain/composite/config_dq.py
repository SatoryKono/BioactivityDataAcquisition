"""Data-quality composite configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.composite.config_validators import (
    validate_optional_threshold,
    validate_threshold_order,
)

if TYPE_CHECKING:
    from bioetl.domain.config.validation import CrossFieldValidation, FieldValidation

__all__ = [
    "CompositeDQConfig",
    "DQOverrideConfig",
]


@dataclass(frozen=True, slots=True)
class DQOverrideConfig:
    """DQ threshold overrides for a specific enricher.

    Allows customizing DQ thresholds per-enricher when defaults
    are too strict or lenient.

    Attributes:
        soft_fail_threshold: Override soft threshold (0.0-1.0).
        hard_fail_threshold: Override hard threshold (0.0-1.0).
    """

    soft_fail_threshold: float | None = None
    hard_fail_threshold: float | None = None

    def __post_init__(self) -> None:
        """Validate threshold values."""
        validate_optional_threshold(self.soft_fail_threshold, "soft_fail_threshold")
        validate_optional_threshold(self.hard_fail_threshold, "hard_fail_threshold")
        validate_threshold_order(self.soft_fail_threshold, self.hard_fail_threshold)


@dataclass(frozen=True, slots=True)
class CompositeDQConfig:
    """Data quality configuration for composite pipelines.

    Extends standard DQConfig with per-enricher overrides.

    Attributes:
        soft_fail_threshold: Default soft threshold for composite.
        hard_fail_threshold: Default hard threshold for composite.
        enricher_overrides: Per-enricher DQ threshold overrides.
        required_fields: Fields required in final Gold output.
        field_validations: Field-level validation bundle for composite Gold.
        cross_field_validations: Cross-field validation bundle for composite Gold.
    """

    soft_fail_threshold: float = 0.10
    hard_fail_threshold: float = 0.50
    enricher_overrides: dict[str, DQOverrideConfig] = field(default_factory=dict)
    required_fields: tuple[str, ...] = ()
    field_validations: tuple[FieldValidation, ...] = ()
    cross_field_validations: tuple[CrossFieldValidation, ...] = ()

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.required_fields, list):
            object.__setattr__(self, "required_fields", tuple(self.required_fields))
        if isinstance(self.field_validations, list):
            object.__setattr__(
                self,
                "field_validations",
                tuple(self.field_validations),
            )
        if isinstance(self.cross_field_validations, list):
            object.__setattr__(
                self,
                "cross_field_validations",
                tuple(self.cross_field_validations),
            )
        self._validate()

    def _validate(self) -> None:
        """Validate DQ configuration."""
        if not 0.0 <= self.soft_fail_threshold <= 1.0:
            raise ValueError(
                f"soft_fail_threshold must be between 0.0 and 1.0, got {self.soft_fail_threshold}"
            )
        if not 0.0 <= self.hard_fail_threshold <= 1.0:
            raise ValueError(
                f"hard_fail_threshold must be between 0.0 and 1.0, got {self.hard_fail_threshold}"
            )
        if self.soft_fail_threshold >= self.hard_fail_threshold:
            raise ValueError(
                "soft_fail_threshold must be less than hard_fail_threshold"
            )
        for enricher_name, override in self.enricher_overrides.items():
            soft = (
                override.soft_fail_threshold
                if override.soft_fail_threshold is not None
                else self.soft_fail_threshold
            )
            hard = (
                override.hard_fail_threshold
                if override.hard_fail_threshold is not None
                else self.hard_fail_threshold
            )
            if soft >= hard:
                raise ValueError(
                    f"enricher '{enricher_name}' effective soft_fail_threshold "
                    f"({soft}) must be less than effective hard_fail_threshold ({hard})"
                )

    def get_enricher_soft_threshold(self, enricher_name: str) -> float:
        """Get effective soft threshold for an enricher.

        Args:
            enricher_name: Enricher pipeline name.

        Returns:
            Enricher soft threshold.
        """
        override = self.enricher_overrides.get(enricher_name)
        if override and override.soft_fail_threshold is not None:
            return override.soft_fail_threshold
        return self.soft_fail_threshold

    def get_enricher_hard_threshold(self, enricher_name: str) -> float:
        """Get effective hard threshold for an enricher.

        Args:
            enricher_name: Enricher pipeline name.

        Returns:
            Enricher hard threshold.
        """
        override = self.enricher_overrides.get(enricher_name)
        if override and override.hard_fail_threshold is not None:
            return override.hard_fail_threshold
        return self.hard_fail_threshold
