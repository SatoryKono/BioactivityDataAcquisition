"""InChI Value Object for BioETL domain.

RF-NORM-07: Unified InChI validation across ChEMBL and PubChem.
"""

from __future__ import annotations

from bioetl.domain.value_objects.base import ValueObject


class InChI(ValueObject[str]):
    """IUPAC InChI identifier value object.

    InChI (International Chemical Identifier) strings always start with
    ``InChI=`` followed by version and layer information.

    RF-NORM-07: Unified InChI validation across ChEMBL and PubChem.

    Invariants:
        - Must start with ``InChI=``
        - Normalized by stripping whitespace
    """

    __slots__ = ()
    _value: str

    _PREFIX = "InChI="

    def _validate(self, value: str) -> str:
        """Validate and normalize InChI string.

        Args:
            value: Raw InChI string.

        Returns:
            Stripped InChI string.

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"InChI must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("InChI cannot be empty")

        if not normalized.startswith(self._PREFIX):
            raise ValueError(f"InChI must start with '{self._PREFIX}': {value!r}")
        # Require version + at least one layer after prefix (reject bare InChI=).
        suffix = normalized[len(self._PREFIX) :]
        if not suffix or "/" not in suffix:
            raise ValueError(
                f"InChI must include version and layer after '{self._PREFIX}': {value!r}"
            )

        return normalized

    @classmethod
    def from_raw(cls, raw: str | None) -> InChI | None:
        """Create InChI from raw string with normalization.

        Args:
            raw: Raw InChI string or None.

        Returns:
            InChI if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


__all__ = ["InChI"]
