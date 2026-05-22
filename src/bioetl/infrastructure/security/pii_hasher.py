"""SHA256-based PII hasher implementation.

Implements RULES.md §5.4 - Silver layer MUST hash PII fields using
sha256(lowercase(value) + SALT).

Environment variables:
    BIOETL_PII_SALT_CURRENT: Current salt for hashing (REQUIRED in production)
    BIOETL_PII_SALT_NEXT: Next salt for rotation (optional)
    BIOETL_SALT_ROTATION_ACTIVE: Whether rotation is in progress (optional)
"""

from __future__ import annotations

__all__ = ["SaltConfig", "Sha256PiiHasher"]


import hashlib
import os
import unicodedata
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


@dataclass(frozen=True, slots=True)
class SaltConfig:
    """Configuration for PII salt management.

    Attributes:
        current_salt: Current salt for hashing (required).
        next_salt: Next salt for rotation (optional).
        rotation_active: Whether salt rotation is in progress.
    """

    current_salt: str
    next_salt: str | None = None
    rotation_active: bool = False

    def __post_init__(self) -> None:
        """Validate salt configuration."""
        if not self.current_salt:
            raise ValueError("PII salt cannot be empty")
        if len(self.current_salt) < 32:
            raise ValueError(
                f"PII salt must be at least 32 characters, got {len(self.current_salt)}"
            )

    @classmethod
    def from_settings(cls, settings: Settings) -> SaltConfig:
        """Create SaltConfig from application settings.

        Raises:
            ValueError: If pii_salt_current is not set or too short.

        Returns:
            SaltConfig instance.

        Args:
            settings: Settings object.
        """
        current = (
            settings.pii_salt_current.get_secret_value()
            if settings.pii_salt_current
            else ""
        )
        next_salt = (
            settings.pii_salt_next.get_secret_value()
            if settings.pii_salt_next
            else None
        )
        rotation_active = settings.pii_salt_rotation_active

        return cls(
            current_salt=current,
            next_salt=next_salt,
            rotation_active=rotation_active,
        )

    @classmethod
    def from_env(cls) -> SaltConfig:
        """Create SaltConfig directly from environment variables.

        Expected variables:
        - BIOETL_PII_SALT_CURRENT (required)
        - BIOETL_PII_SALT_NEXT (optional)
        - BIOETL_SALT_ROTATION_ACTIVE (optional: true/1/yes/on)

        Returns:
            The SaltConfig result.
        """
        current = os.getenv("BIOETL_PII_SALT_CURRENT", "")
        raw_next = os.getenv("BIOETL_PII_SALT_NEXT")
        next_salt = raw_next or None
        rotation_active = os.getenv(
            "BIOETL_SALT_ROTATION_ACTIVE", ""
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        return cls(
            current_salt=current,
            next_salt=next_salt,
            rotation_active=rotation_active,
        )


@dataclass
class Sha256PiiHasher:
    """SHA256-based implementation of PiiHasherPort.

    Hashes PII values using SHA256 with salt for Silver layer compliance.

    The hashing algorithm:
    1. Normalize: NFKC unicode normalization
    2. Lowercase: value.lower()
    3. Strip: value.strip()
    4. Concatenate: normalized_value + salt
    5. Hash: SHA256 hex digest

    This ensures:
    - Deterministic output for same input
    - Resistance to rainbow table attacks (salted)
    - Unicode normalization for cross-platform consistency

    Example:
        >>> config = SaltConfig(current_salt="a" * 64)
        >>> hasher = Sha256PiiHasher(config)
        >>> hasher.hash_value("John Doe")
        '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069'

    Implements:
        PiiHasherPort: Domain port for PII hashing.
    """

    salt_config: SaltConfig
    _salt_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Compute salt ID for tracking."""
        # Use first 8 chars of salt hash as ID
        salt_hash = hashlib.sha256(
            self.salt_config.current_salt.encode("utf-8")
        ).hexdigest()
        object.__setattr__(self, "_salt_id", salt_hash[:8])

    @cached_property
    def _salt_bytes(self) -> bytes:
        """Pre-encode salt for performance."""
        return self.salt_config.current_salt.encode("utf-8")

    def _normalize(self, value: str) -> str:
        """Normalize value before hashing.

        Applies:
        - NFKC unicode normalization
        - Lowercase conversion
        - Whitespace stripping

        Args:
            value: Raw PII value.

        Returns:
            Normalized value ready for hashing.
        """
        # NFKC normalization for unicode consistency
        normalized = unicodedata.normalize("NFKC", value)
        # Lowercase and strip
        return normalized.lower().strip()

    def hash_value(self, value: str | None) -> str | None:
        """Hash a single PII value.

        Args:
            value: The PII value to hash (e.g., author name).
                   If None or empty string, returns None.

        Returns:
            SHA256 hex digest of normalized(value) + salt,
            or None if input is None/empty.
        """
        if value is None:
            return None

        # Treat empty/whitespace-only as None
        normalized = self._normalize(value)
        if not normalized:
            return None

        # Hash: sha256(normalized_value + salt)
        data = normalized.encode("utf-8") + self._salt_bytes
        return hashlib.sha256(data).hexdigest()

    def hash_list(self, values: list[str] | None) -> list[str] | None:
        """Hash a list of PII values.

        Args:
            values: List of PII values (e.g., list of author names).
                    If None, returns None.

        Returns:
            List of SHA256 hex digests (None values filtered out),
            or None if input is None.
        """
        if values is None:
            return None

        result = []
        for v in values:
            hashed = self.hash_value(v)
            if hashed is not None:
                result.append(hashed)

        return result

    def get_salt_id(self) -> str:
        """Get identifier for current salt (for audit/tracking).

        Returns:
            First 8 characters of SHA256(salt).
            Used for tracking which salt version was used.
        """
        return self._salt_id

    @classmethod
    def from_settings(cls, settings: Settings) -> Sha256PiiHasher:
        """Create hasher from application settings.

        Raises:
            ValueError: If pii_salt_current is not set.

        Returns:
            Configured Sha256PiiHasher instance.

        Args:
            settings: Settings object.
        """
        return cls(salt_config=SaltConfig.from_settings(settings))

    @classmethod
    def from_env(cls) -> Sha256PiiHasher:
        """Create hasher directly from environment variables.

        Returns:
            The Sha256PiiHasher result.
        """
        return cls(salt_config=SaltConfig.from_env())
