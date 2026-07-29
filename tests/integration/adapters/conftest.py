# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Shared adapter integration fixtures."""

from __future__ import annotations

from tests.integration.adapters.pubmed_integration_support import (
    http_client,
    mock_logger,
    pubmed_adapter,
)

__all__ = ["http_client", "mock_logger", "pubmed_adapter"]
