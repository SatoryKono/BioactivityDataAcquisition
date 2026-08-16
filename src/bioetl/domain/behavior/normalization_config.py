"""Configuration for normalization services.

Injectable configuration for bioactivity normalization, allowing
customization of validation thresholds, aggregation methods, and
unit conversion preferences.

Pure domain configuration (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "ConcentrationRangeConfig",
    "NormalizationConfig",
    "PChemblRangeConfig",
]

_VALID_AGGREGATION_METHODS = frozenset({"mean", "median", "geometric_mean"})


@dataclass(frozen=True, slots=True)
class ConcentrationRangeConfig:
    """Configuration for concentration validation ranges.

    Attributes:
        min_molar: Minimum valid concentration in molar (M).
        max_molar: Maximum valid concentration in molar (M).
    """

    min_molar: float = 1e-15  # 1 femtomolar
    max_molar: float = 1e-1  # 100 millimolar

    def __post_init__(self) -> None:
        """Validate range configuration."""
        if self.min_molar <= 0:
            raise ValueError("min_molar must be positive")
        if self.max_molar <= 0:
            raise ValueError("max_molar must be positive")
        if self.min_molar >= self.max_molar:
            raise ValueError("min_molar must be less than max_molar")


@dataclass(frozen=True, slots=True)
class PChemblRangeConfig:
    """Configuration for pChEMBL value validation.

    Attributes:
        min_value: Minimum valid pChEMBL value.
        max_value: Maximum valid pChEMBL value.
        typical_min: Minimum for typical drug-like activity.
        typical_max: Maximum for typical drug-like activity.
    """

    min_value: float = 0.0
    max_value: float = 14.0
    typical_min: float = 2.0
    typical_max: float = 12.0

    def __post_init__(self) -> None:
        """Validate pChEMBL range configuration."""
        self._validate_absolute_range()
        self._validate_typical_range()

    def _validate_absolute_range(self) -> None:
        """Validate absolute min/max range."""
        if self.min_value < 0:
            raise ValueError("min_value cannot be negative")
        if self.max_value > 15:
            raise ValueError("max_value exceeds physical limit")
        if self.min_value >= self.max_value:
            raise ValueError("min_value must be less than max_value")

    def _validate_typical_range(self) -> None:
        """Validate typical range is ordered and within absolute bounds."""
        if self.typical_min >= self.typical_max:
            raise ValueError("typical_min must be less than typical_max")
        if self.typical_min < self.min_value or self.typical_max > self.max_value:
            raise ValueError(
                "typical_min and typical_max must fall within "
                f"[{self.min_value}, {self.max_value}]"
            )


@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    """Master configuration for normalization services.

    Centralizes all configuration for unit conversion, validation,
    and aggregation services. Immutable for thread safety.

    Attributes:
        default_output_unit: Default output unit for concentrations.
        strict_validation: Enable strict range validation.
        default_aggregation_method: Default method for aggregation.
        concentration_range: Configuration for concentration validation.
        pchembl_range: Configuration for pChEMBL validation.
        potency_threshold: pChEMBL threshold for "potent" classification.
        high_potency_threshold: pChEMBL threshold for "highly potent".

    Example:
        >>> config = NormalizationConfig(
        ...     strict_validation=True,
        ...     potency_threshold=6.0,
        ... )
        >>> config.default_output_unit
        'nM'
    """

    default_output_unit: str = "nM"
    strict_validation: bool = False
    default_aggregation_method: Literal["mean", "median", "geometric_mean"] = "median"
    concentration_range: ConcentrationRangeConfig = field(
        default_factory=ConcentrationRangeConfig
    )
    pchembl_range: PChemblRangeConfig = field(default_factory=PChemblRangeConfig)
    potency_threshold: float = 5.0  # pChEMBL >= 5 = active at 10 µM
    high_potency_threshold: float = 7.0  # pChEMBL >= 7 = active at 100 nM

    def __post_init__(self) -> None:
        """Validate configuration."""
        self._validate_threshold_order()
        self._validate_threshold_bounds()
        self._validate_aggregation_method()

    def _validate_threshold_order(self) -> None:
        """Validate potency thresholds are non-negative and ordered."""
        if self.potency_threshold < 0:
            raise ValueError("potency_threshold cannot be negative")
        if self.high_potency_threshold < 0:
            raise ValueError("high_potency_threshold cannot be negative")
        if self.high_potency_threshold < self.potency_threshold:
            raise ValueError("high_potency_threshold must be >= potency_threshold")

    def _validate_threshold_bounds(self) -> None:
        """Validate potency thresholds against the configured pChEMBL maximum."""
        pchembl_max = self.pchembl_range.max_value
        if self.potency_threshold > pchembl_max:
            raise ValueError(
                f"potency_threshold cannot exceed pChEMBL max_value ({pchembl_max})"
            )
        if self.high_potency_threshold > pchembl_max:
            raise ValueError(
                "high_potency_threshold cannot exceed pChEMBL max_value "
                f"({pchembl_max})"
            )

    def _validate_aggregation_method(self) -> None:
        """Validate the configured aggregation method."""
        if self.default_aggregation_method not in _VALID_AGGREGATION_METHODS:
            raise ValueError(
                f"Invalid aggregation method: {self.default_aggregation_method}"
            )

    @classmethod
    def strict(cls) -> NormalizationConfig:
        """Create configuration with strict validation enabled.

        Returns:
            NormalizationConfig with strict_validation=True.
        """
        return cls(strict_validation=True)

    @classmethod
    def for_screening(cls) -> NormalizationConfig:
        """Create configuration optimized for HTS screening data.

        Uses mean aggregation (replicates are typically consistent)
        and relaxed validation thresholds.

        Returns:
            NormalizationConfig for screening assays.
        """
        return cls(
            default_aggregation_method="mean",
            strict_validation=False,
            potency_threshold=4.0,  # More permissive for screening hits
            concentration_range=ConcentrationRangeConfig(
                min_molar=1e-12,
                max_molar=1e-2,
            ),
        )

    @classmethod
    def for_medicinal_chemistry(cls) -> NormalizationConfig:
        """Create configuration for medicinal chemistry data.

        Uses median aggregation (robust against outliers)
        and stricter validation for high-quality data.

        Returns:
            NormalizationConfig for med-chem assays.
        """
        return cls(
            default_aggregation_method="median",
            strict_validation=True,
            potency_threshold=6.0,  # Higher bar for med-chem
            high_potency_threshold=8.0,
        )
