"""Anomaly type aliases for infrastructure detection code."""

from __future__ import annotations

__all__ = ["AnomalyRecord", "AnomalySeverity", "AnomalyType"]

from bioetl.domain.value_objects.dq_anomaly import (
    DQAnomaly as AnomalyRecord,
)
from bioetl.domain.value_objects.dq_anomaly import (
    DQAnomalySeverity as AnomalySeverity,
)
from bioetl.domain.value_objects.dq_anomaly import (
    DQAnomalyType as AnomalyType,
)
