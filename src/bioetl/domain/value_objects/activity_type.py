"""Bioactivity type enum and classification helpers."""

from __future__ import annotations

from enum import StrEnum


class ActivityType(StrEnum):
    """Types of bioactivity measurements in drug discovery."""

    IC50 = "IC50"
    IC90 = "IC90"
    KI = "Ki"
    KD = "Kd"
    EC50 = "EC50"
    AC50 = "AC50"
    ED50 = "ED50"
    GI50 = "GI50"
    LC50 = "LC50"
    LD50 = "LD50"
    ID50 = "ID50"
    POTENCY = "Potency"
    INHIBITION = "Inhibition"
    PERCENT_INHIBITION = "% Inhibition"
    ACTIVITY = "Activity"
    RATIO = "Ratio"

    @classmethod
    def from_string(cls, s: str) -> ActivityType:
        """Parse activity type from string.

        Args:
            s: Activity type label such as 'IC50', 'Ki', 'EC50'.

        Returns:
            Corresponding ActivityType enum member.
        """
        if s is None:
            raise ValueError("Unknown activity type: None")
        normalized = s.strip().upper()
        type_map = {
            "IC50": cls.IC50,
            "IC90": cls.IC90,
            "KI": cls.KI,
            "KD": cls.KD,
            "EC50": cls.EC50,
            "AC50": cls.AC50,
            "ED50": cls.ED50,
            "GI50": cls.GI50,
            "LC50": cls.LC50,
            "LD50": cls.LD50,
            "ID50": cls.ID50,
            "POTENCY": cls.POTENCY,
            "INHIBITION": cls.INHIBITION,
            "% INHIBITION": cls.PERCENT_INHIBITION,
            "ACTIVITY": cls.ACTIVITY,
            "RATIO": cls.RATIO,
        }
        activity_type = type_map.get(normalized)
        if activity_type is None:
            raise ValueError(f"Unknown activity type: {s!r}")
        return activity_type

    def is_inhibition_type(self) -> bool:
        """Check if this is an inhibition-type measurement."""
        return self in {
            ActivityType.IC50,
            ActivityType.IC90,
            ActivityType.KI,
            ActivityType.INHIBITION,
            ActivityType.PERCENT_INHIBITION,
        }

    def is_binding_type(self) -> bool:
        """Check if this is a binding affinity measurement."""
        return self in {
            ActivityType.KI,
            ActivityType.KD,
        }


__all__ = ["ActivityType"]
