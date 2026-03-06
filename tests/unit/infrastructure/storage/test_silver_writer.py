"""Legacy SilverWriter monolith placeholder.

Tests were split into `tests/unit/infrastructure/storage/silver_writer/`
for lower structural debt and faster diagnosis by concern.
"""

from __future__ import annotations

from .silver_writer.conftest import (
    mock_metadata_coordinator,
    noop_logger,
    valid_records,
)

__all__ = ["mock_metadata_coordinator", "noop_logger", "valid_records"]
