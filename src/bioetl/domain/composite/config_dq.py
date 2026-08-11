"""Data-quality composite configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
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
        from bioetl.domain.immutability import freeze_fields

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
        # Detach caller-owned override mapping for frozen determinism.
        freeze_fields(self, ("enricher_overrides",))
        self._validate()

    def _require_unit_interval(self, name: str, value: float) -> None:
        if 0.0 <= value <= 1.0:
            return
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")

    def _require_soft_less_than_hard(
        self,
        soft: float,
        hard: float,
        *,
        enricher_name: str | None = None,
    ) -> None:
        if soft < hard:
            return
        if enricher_name is None:
            raise ValueError(
                "soft_fail_threshold must be less than hard_fail_threshold"
            )
        raise ValueError(
            f"enricher '{enricher_name}' effective soft_fail_threshold "
            f"({soft}) must be less than effective hard_fail_threshold ({hard})"
        )

    def _override_or_default(
        self, override_value: float | None, default: float
    ) -> float:
        if override_value is None:
            return default
        return override_value

    def _effective_override_thresholds(
        self,
        override: object,
    ) -> tuple[float, float]:
        soft = self._override_or_default(
            override.soft_fail_threshold,  # type: ignore[attr-defined]
            self.soft_fail_threshold,
        )
        hard = self._override_or_default(
            override.hard_fail_threshold,  # type: ignore[attr-defined]
            self.hard_fail_threshold,
        )
        return soft, hard

    def _validate(self) -> None:
        """Validate DQ configuration."""
        self._require_unit_interval("soft_fail_threshold", self.soft_fail_threshold)
        self._require_unit_interval("hard_fail_threshold", self.hard_fail_threshold)
        self._require_soft_less_than_hard(
            self.soft_fail_threshold,
            self.hard_fail_threshold,
        )
        for enricher_name, override in self.enricher_overrides.items():
            soft, hard = self._effective_override_thresholds(override)
            self._require_soft_less_than_hard(soft, hard, enricher_name=enricher_name)

    def get_enricher_soft_threshold(self, enricher_name: str) -> float:
        """Get effective soft threshold for an enricher.

        Args:
            enricher_name: Enricher pipeline name.

        Returns:
            Enricher soft threshold.
        """
        override = self.enricher_overrides.get(enricher_name)
        if override is None:
            return self.soft_fail_threshold
        if override.soft_fail_threshold is None:
            return self.soft_fail_threshold
        return override.soft_fail_threshold

    def get_enricher_hard_threshold(self, enricher_name: str) -> float:
        """Get effective hard threshold for an enricher.

        Args:
            enricher_name: Enricher pipeline name.

        Returns:
            Enricher hard threshold.
        """
        override = self.enricher_overrides.get(enricher_name)
        if override is None:
            return self.hard_fail_threshold
        if override.hard_fail_threshold is None:
            return self.hard_fail_threshold
        return override.hard_fail_threshold
