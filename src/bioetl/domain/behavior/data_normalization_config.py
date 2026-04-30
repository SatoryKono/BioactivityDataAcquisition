"""Configuration for data normalization services.

Injectable configuration for text and data normalization, allowing
customization of year validation ranges and other parameters.

Pure domain configuration (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DataNormalizationConfig",
]


@dataclass(frozen=True, slots=True)
class DataNormalizationConfig:
    """Configuration for data normalization services.

    Centralizes all configuration for text and data normalization.
    Immutable for thread safety.

    Attributes:
        min_publication_year: Minimum valid publication year.
        max_publication_year: Maximum valid publication year.
        default_pii_salt: Default salt for PII hashing (should be overridden).

    Example:
        >>> config = DataNormalizationConfig()
        >>> config.min_publication_year
        1500
        >>> config.max_publication_year
        2100

        >>> config = DataNormalizationConfig(min_publication_year=1900)
        >>> config.min_publication_year
        1900
    """

    min_publication_year: int = 1500
    max_publication_year: int = 2100
    default_pii_salt: str = ""

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.min_publication_year < 0:
            raise ValueError("min_publication_year cannot be negative")
        if self.max_publication_year < self.min_publication_year:
            raise ValueError("max_publication_year must be >= min_publication_year")

    @classmethod
    def for_scientific_publications(cls) -> DataNormalizationConfig:
        """Create configuration for scientific publications.

        Uses standard year range [1500, 2100] for scientific literature.

        Returns:
            DataNormalizationConfig with scientific publication defaults.
        """
        return cls()

    @classmethod
    def for_modern_publications(cls) -> DataNormalizationConfig:
        """Create configuration for modern publications only.

        Uses year range [1900, 2100] for more recent literature.

        Returns:
            DataNormalizationConfig with modern publication defaults.
        """
        return cls(min_publication_year=1900)
