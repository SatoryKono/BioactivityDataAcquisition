"""Typed anomaly detection for data quality monitoring.

Implements baseline comparison and threshold-based detection for:
- Record count anomalies (sudden drops/spikes)
- Processing time anomalies
- Error rate anomalies
- Data quality score degradation

Uses Z-score statistical method with Strategy pattern.

Usage:
    detector = AnomalyDetector(baseline_window=7)

    # Update baseline with historical data
    detector.update_baseline("record_count", [1000, 1050, 980, 1020, 1100])

    # Check for anomalies
    anomaly = detector.detect("record_count", 500)
    if anomaly:
        logger.warning(f"DQ anomaly detected: {anomaly}")
"""

from __future__ import annotations

from bioetl.infrastructure.observability.anomaly.detector import AnomalyDetector
from bioetl.infrastructure.observability.anomaly.detectors import (
    DetectorStrategy,
    ZScoreDetector,
)
from bioetl.infrastructure.observability.anomaly.monitor import (
    DataQualityMonitor,
)
from bioetl.infrastructure.observability.anomaly.types import (
    AnomalyRecord,
    AnomalySeverity,
    AnomalyType,
)

__all__ = [
    "AnomalyDetector",
    # Backward-compatible aliases; domain-owned DQAnomaly* is the canonical boundary contract.
    "AnomalyRecord",
    "AnomalySeverity",
    "AnomalyType",
    "DataQualityMonitor",
    "DetectorStrategy",
    "ZScoreDetector",
]
