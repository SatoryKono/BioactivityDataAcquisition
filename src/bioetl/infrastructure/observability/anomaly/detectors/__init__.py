"""Anomaly detection strategies.

Implements Strategy pattern for different detection algorithms.
"""

from bioetl.infrastructure.observability.anomaly.detectors.base import DetectorStrategy
from bioetl.infrastructure.observability.anomaly.detectors.iqr import IQRDetector
from bioetl.infrastructure.observability.anomaly.detectors.mad import MADDetector
from bioetl.infrastructure.observability.anomaly.detectors.zscore import ZScoreDetector

__all__ = [
    "DetectorStrategy",
    "IQRDetector",
    "MADDetector",
    "ZScoreDetector",
]
