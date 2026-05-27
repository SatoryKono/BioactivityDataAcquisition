"""Facade for the run-ledger ownership package."""

from __future__ import annotations

# Compatibility wrapper: re-export ownership-package implementation only.
from bioetl.application.services.control_plane.ledger.service import *  # noqa: F403
