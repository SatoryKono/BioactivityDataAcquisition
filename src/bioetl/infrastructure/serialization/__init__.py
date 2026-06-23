"""JSON serialization adapters.

Provides pluggable JSON encoder implementations:
- StdLibJsonEncoder: Standard library json (fallback, always available)
- OrjsonEncoder: orjson-based encoder (high performance, optional)

Use get_json_encoder() factory function to get the configured encoder.
"""

from __future__ import annotations

from bioetl.infrastructure.serialization.encoders import (
    OrjsonEncoder,
    StdLibJsonEncoder,
    get_json_encoder,
)

__all__ = [
    "OrjsonEncoder",
    "StdLibJsonEncoder",
    "get_json_encoder",
]
