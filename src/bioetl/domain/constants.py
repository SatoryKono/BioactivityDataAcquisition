"""Common domain constants.
"""

from typing import Final

# Default filtering types for Gold layer (ChEMBL)
DEFAULT_GOLD_FILTER_TYPES: Final[list[str]] = [
    "IC50",
    "Ki",
    "EC50",
    "Kd",
    "AC50",
    "GI50",
]
