"""Molecular descriptor Value Objects for BioETL domain.

Provides unified validation for physicochemical properties shared across
molecule/compound pipelines (ChEMBL, PubChem).

RF-NORM-05: Normalization Unification Plan.

Each Value Object uses canonical bounds from ``schemas.constants`` and
offers a ``from_raw`` factory that returns ``None`` for invalid input
(consistent with the existing VO pattern in this project).

Usage::

    from bioetl.domain.value_objects.molecular_descriptors import (
        HydrogenBondCount,
        LogP,
    )

    hba = HydrogenBondCount.from_raw("5")
    assert hba is not None and hba.value == 5

    logp = LogP.from_raw(-2.5)
    assert logp is not None and logp.value == -2.5
"""

from __future__ import annotations

import math
from typing import (
    Any,  # Any: needed for _validate override accepting Any from base class
)

from bioetl.domain.schemas.constants import (
    CANONICAL_HBA_COUNT_RANGE,
    CANONICAL_HEAVY_ATOM_COUNT_RANGE,
    CANONICAL_LOGP_RANGE,
    CANONICAL_POLAR_SURFACE_AREA_RANGE,
    CANONICAL_ROTATABLE_BOND_COUNT_RANGE,
)
from bioetl.domain.value_objects.base import ValueObject

# ============================================================================
# Helpers
# ============================================================================


def _coerce_int(value: object) -> int:
    """Coerce *value* to ``int``, raising ``ValueError`` on failure."""
    if isinstance(value, bool):
        raise ValueError(f"Expected int, got {type(value).__name__}")
    if isinstance(value, (int, float)):
        f = float(value)
        if not math.isfinite(f):
            raise ValueError(f"Cannot convert {value} to int")
        return int(f)
    try:
        return int(str(value).strip())
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Cannot convert {value!r} to int") from exc


def _coerce_float(value: object) -> float:
    """Coerce *value* to ``float``, raising ``ValueError`` on failure."""
    if isinstance(value, bool):
        raise ValueError(f"Expected float, got {type(value).__name__}")
    try:
        f = float(str(value).strip())
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Cannot convert {value!r} to float") from exc
    if math.isnan(f) or math.isinf(f):
        raise ValueError(f"Invalid float: {value}")
    return f


# ============================================================================
# Integer descriptor VOs
# ============================================================================


class _BoundedIntVO(ValueObject[int]):
    """Base for bounded non-negative integer descriptors."""

    __slots__ = ()
    _value: int

    # Subclasses MUST override these.
    _MIN: int
    _MAX: int
    _LABEL: str

    def _validate(
        self,
        value: Any,  # Any: accepts str|int|float for coercion beyond base T=int
    ) -> int:
        n = _coerce_int(value)
        if not self._MIN <= n <= self._MAX:
            raise ValueError(f"{self._LABEL} {n} outside [{self._MIN}, {self._MAX}]")
        return n

    @classmethod
    def from_raw(
        cls,
        raw: object,
    ) -> _BoundedIntVO | None:
        """Create from raw value; returns ``None`` on invalid input.

        Args:
            raw: Raw input value.

        Returns:
            New instance constructed from the input.
        """
        if raw is None:
            return None
        try:
            return cls(_coerce_int(raw))
        except ValueError:
            return None


class HydrogenBondCount(_BoundedIntVO):
    """Hydrogen-bond donor or acceptor count.

    Canonical range from ``CANONICAL_HBA_COUNT_RANGE`` / ``CANONICAL_HBD_COUNT_RANGE``.
    Uses the wider of the two (they are identical by design).
    """

    __slots__ = ()
    _MIN, _MAX = CANONICAL_HBA_COUNT_RANGE
    _LABEL = "HydrogenBondCount"


class RotatableBondCount(_BoundedIntVO):
    """Rotatable bond count."""

    __slots__ = ()
    _MIN, _MAX = CANONICAL_ROTATABLE_BOND_COUNT_RANGE
    _LABEL = "RotatableBondCount"


class HeavyAtomCount(_BoundedIntVO):
    """Non-hydrogen (heavy) atom count."""

    __slots__ = ()
    _MIN, _MAX = CANONICAL_HEAVY_ATOM_COUNT_RANGE
    _LABEL = "HeavyAtomCount"


# ============================================================================
# Float descriptor VOs
# ============================================================================


class _BoundedFloatVO(ValueObject[float]):
    """Base for bounded float descriptors."""

    __slots__ = ()
    _value: float

    _MIN: float
    _MAX: float
    _LABEL: str
    _PRECISION: int = 10

    def _validate(
        self,
        value: Any,  # Any: accepts str|int|float for coercion beyond base T=float
    ) -> float:
        f = _coerce_float(value)
        if not self._MIN <= f <= self._MAX:
            raise ValueError(f"{self._LABEL} {f} outside [{self._MIN}, {self._MAX}]")
        return round(f, self._PRECISION)

    @classmethod
    def from_raw(
        cls,
        raw: object,
    ) -> _BoundedFloatVO | None:
        """Create from raw value; returns ``None`` on invalid input.

        Args:
            raw: Raw input value.

        Returns:
            New instance constructed from the input.
        """
        if raw is None:
            return None
        try:
            return cls(_coerce_float(raw))
        except ValueError:
            return None


class PolarSurfaceArea(_BoundedFloatVO):
    """Topological polar surface area (Å²)."""

    __slots__ = ()
    _MIN, _MAX = CANONICAL_POLAR_SURFACE_AREA_RANGE
    _LABEL = "PolarSurfaceArea"


class LogP(_BoundedFloatVO):
    """Octanol-water partition coefficient (ALogP / XLogP)."""

    __slots__ = ()
    _MIN, _MAX = CANONICAL_LOGP_RANGE
    _LABEL = "LogP"


__all__ = [
    "HeavyAtomCount",
    "HydrogenBondCount",
    "LogP",
    "PolarSurfaceArea",
    "RotatableBondCount",
]
