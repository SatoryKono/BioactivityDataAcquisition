"""Version formatting utilities for ChEMBL data sources.

This module contains domain logic for formatting version strings.
The formatting rules are business logic that belongs in the domain layer,
not in infrastructure (where raw data is fetched).
"""

from __future__ import annotations

CHEMBL_VERSION_PREFIX = "chembl_"
UNKNOWN_VERSION = "unknown"


def format_chembl_version(raw_version: str) -> str:
    """Format raw ChEMBL version to standard format.

    Args:
        raw_version: Raw version string from API (e.g., '34', '35').

    Returns:
        Formatted version string (e.g., 'chembl_34', 'chembl_35').
        Returns 'unknown' if raw_version is empty or 'unknown'.

    Examples:
        >>> format_chembl_version('34')
        'chembl_34'
        >>> format_chembl_version('unknown')
        'unknown'
        >>> format_chembl_version('')
        'unknown'
        >>> format_chembl_version('ChEMBL_36')
        'chembl_36'
    """
    if not raw_version or raw_version == UNKNOWN_VERSION:
        return UNKNOWN_VERSION

    # Already formatted (case-insensitive check) - normalize to lowercase
    lower_version = raw_version.lower()
    if lower_version.startswith(CHEMBL_VERSION_PREFIX):
        return lower_version

    return f"{CHEMBL_VERSION_PREFIX}{raw_version}"


class ChemblVersionFormatter:
    """Formatter for ChEMBL version strings.

    Stateless service that encapsulates version formatting logic.
    Can be injected as a dependency for better testability.

    Example:
        >>> formatter = ChemblVersionFormatter()
        >>> formatter.format('34')
        'chembl_34'
    """

    @staticmethod
    def format(raw_version: str) -> str:
        """Format raw version to standard ChEMBL format.

        Args:
            raw_version: Raw version from extraction service.

        Returns:
            Formatted version string.
        """
        return format_chembl_version(raw_version)

    @staticmethod
    def is_valid(version: str) -> bool:
        """Check if version string is valid (not unknown).

        Args:
            version: Version string to check.

        Returns:
            True if version is valid, False otherwise.
        """
        return bool(version) and version != UNKNOWN_VERSION
