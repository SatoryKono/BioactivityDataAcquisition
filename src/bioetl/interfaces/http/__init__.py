"""HTTP interface module for BioETL.

Provides HTTP endpoints for health checks and monitoring.
"""

from __future__ import annotations

from bioetl.interfaces.http.health_server import HealthServer

__all__ = ["HealthServer"]
