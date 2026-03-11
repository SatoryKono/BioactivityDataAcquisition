"""AnomalyRecord detection strategies.

Implements Strategy pattern for different detection algorithms.
"""

from __future__ import annotations

from bioetl.infrastructure.observability.anomaly.detectors.base import DetectorStrategy
from bioetl.infrastructure.observability.anomaly.detectors.zscore import ZScoreDetector

__all__ = [
    "DetectorStrategy",
    "ZScoreDetector",
]
