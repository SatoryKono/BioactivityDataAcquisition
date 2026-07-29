# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for shared source-metadata capability helpers."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.common.source_metadata_capability import (
    SourceMetadataCollectorProtocol,
    clear_source_metadata_collector,
    consume_source_metadata,
    get_request_count,
)

pytestmark = pytest.mark.unit


def test_request_collector_satisfies_source_metadata_protocol() -> None:
    collector = APIRequestCollector()

    assert isinstance(collector, SourceMetadataCollectorProtocol)


def test_consume_source_metadata_returns_snapshot_and_clears_collector() -> None:
    collector = APIRequestCollector()
    collector.record_request(
        url="https://example.org/items?query=test",
        duration_ms=42.0,
        status_code=200,
    )

    metadata = consume_source_metadata(
        collector=collector,
        url="https://example.org",
        default_api_version="v1",
        query_string="query=test",
    )

    assert metadata.url == "https://example.org"
    assert metadata.api_version == "v1"
    assert metadata.query_string == "query=test"
    assert metadata.total_requests == 1
    assert get_request_count(collector=collector) == 0


def test_consume_source_metadata_prefers_explicit_api_version() -> None:
    collector = APIRequestCollector()

    metadata = consume_source_metadata(
        collector=collector,
        url="https://example.org",
        api_version="v2",
        default_api_version="v1",
    )

    assert metadata.api_version == "v2"


def test_clear_source_metadata_collector_resets_request_count() -> None:
    collector = APIRequestCollector()
    collector.record_request(url="https://example.org/items", duration_ms=10.0)

    assert get_request_count(collector=collector) == 1

    clear_source_metadata_collector(collector=collector)

    assert get_request_count(collector=collector) == 0
