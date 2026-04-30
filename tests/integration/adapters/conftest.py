"""Shared adapter integration fixtures."""

from __future__ import annotations

from tests.integration.adapters.pubmed_integration_support import (
    http_client,
    mock_logger,
    pubmed_adapter,
)

__all__ = ["http_client", "mock_logger", "pubmed_adapter"]
