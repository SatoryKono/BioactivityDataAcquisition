"""Compatibility re-export — implementation lives in `bioetl.application.services.quality.data_quality_anomalies`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.quality.data_quality_anomalies import *  # noqa: F403
from bioetl.application.services.quality.data_quality_anomalies import __all__ as __all__
