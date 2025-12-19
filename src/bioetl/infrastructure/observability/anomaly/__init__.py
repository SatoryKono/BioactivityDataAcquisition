"""Anomaly detection for data quality monitoring.

Implements baseline comparison and threshold-based detection for:
- Record count anomalies (sudden drops/spikes)
- Processing time anomalies
- Error rate anomalies
- Data quality score degradation

Uses statistical methods (Z-score, IQR, MAD) with Strategy pattern.

Usage:
    detector = AnomalyDetector(baseline_window=7)

    # Update baseline with historical data
    detector.update_baseline("record_count", [1000, 1050, 980, 1020, 1100])

    # Check for anomalies
    anomaly = detector.detect("record_count", 500)
    if anomaly:
        logger.warning(f"Anomaly detected: {anomaly}")
"""

from bioetl.infrastructure.observability.anomaly.detector import AnomalyDetector
from bioetl.infrastructure.observability.anomaly.detectors import (
    DetectorStrategy,
    IQRDetector,
    MADDetector,
    ZScoreDetector,
)
from bioetl.infrastructure.observability.anomaly.monitor import DataQualityMonitor
from bioetl.infrastructure.observability.anomaly.types import (
    Anomaly,
    AnomalySeverity,
    AnomalyType,
)

__all__ = [
    "Anomaly",
    "AnomalyDetector",
    "AnomalySeverity",
    "AnomalyType",
    "DataQualityMonitor",
    "DetectorStrategy",
    "IQRDetector",
    "MADDetector",
    "ZScoreDetector",
]
