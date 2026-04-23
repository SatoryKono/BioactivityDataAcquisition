"""Local composite-facing aliases for domain port contracts.

This module intentionally concentrates composite runtime references to
``bioetl.domain.ports`` behind one application-local import seam so the
composite package does not fan out repeated direct cross-layer imports.
"""

from __future__ import annotations

import bioetl.domain.ports as _domain_ports

ClockPort = _domain_ports.ClockPort
CompositeCheckpointPort = _domain_ports.CompositeCheckpointPort
DeltaReaderPort = _domain_ports.DeltaReaderPort
ExecutionMetricsReadablePort = _domain_ports.ExecutionMetricsReadablePort
ExecutionMetricsRunnerPort = _domain_ports.ExecutionMetricsRunnerPort
LockPort = _domain_ports.LockPort
LoggerPort = _domain_ports.LoggerPort
MetricsPort = _domain_ports.MetricsPort
QuarantinePort = _domain_ports.QuarantinePort
RunLedgerPort = _domain_ports.RunLedgerPort
TracingPort = _domain_ports.TracingPort

__all__ = [
    "ClockPort",
    "CompositeCheckpointPort",
    "DeltaReaderPort",
    "ExecutionMetricsReadablePort",
    "ExecutionMetricsRunnerPort",
    "LockPort",
    "LoggerPort",
    "MetricsPort",
    "QuarantinePort",
    "RunLedgerPort",
    "TracingPort",
]
