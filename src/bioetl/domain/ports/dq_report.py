"""Backward-compatible re-export for quality DQ report ports.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.quality.dq_report import (
    BronzeDQAnalyzerPort,
    DQReportWriterPort,
    GoldDQAnalyzerPort,
    SilverDQAnalyzerPort,
)

__all__ = [
    "BronzeDQAnalyzerPort",
    "DQReportWriterPort",
    "GoldDQAnalyzerPort",
    "SilverDQAnalyzerPort",
]
