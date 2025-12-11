"""HTTP session factory for infrastructure layer.

This module provides a factory function for creating HTTP sessions,
encapsulating the dependency on the requests library.
"""

from __future__ import annotations

from typing import Any


def create_http_session() -> Any:
    """Create HTTP session instance.

    Returns:
        requests.Session instance configured with default settings.
    """
    import requests

    return requests.Session()


__all__ = ["create_http_session"]
