"""Canonical DQ services factory module.

Provides the DQ analyzer/report-writer factory.
The legacy ``factory`` module remains for backward compatibility.
"""

from __future__ import annotations

from bioetl.composition.factories.dq.factory import DQServicesFactory

__all__ = ["DQServicesFactory"]
