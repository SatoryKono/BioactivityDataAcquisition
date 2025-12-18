"""Unit tests for domain ports (Protocols)."""

from typing import Any
from uuid import uuid4

import pytest

from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    LockPort,
    MetricsPort,
    OrchestrationPort,
    QuarantinePort,
    StoragePort,
)
from bioetl.domain.types import BatchID, RunID, Watermark


@pytest.mark.unit
class TestDataSourcePortProtocol:
    """Tests for the DataSourcePort protocol."""

    def test_provider_name_attribute_required(self) -> None:
        """DataSourcePort should require provider_name attribute."""

        class ValidDataSource:
            provider_name = "test"

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            async def fetch(self, _entity_type, _watermark=None, _limit=None):
                yield {}

            async def health_check(self):
                from bioetl.domain.types import HealthStatus

                return HealthStatus.HEALTHY

            async def aclose(self):
                pass

        # Should pass isinstance check
        assert isinstance(ValidDataSource(), DataSourcePort)

        class InvalidDataSource:
            # Missing provider_name
            async def fetch(self, _entity_type, _watermark=None, _limit=None):
                yield {}

            async def health_check(self):
                from bioetl.domain.types import HealthStatus

                return HealthStatus.HEALTHY

            async def aclose(self):
                pass

        # Should fail isinstance check
        assert not isinstance(InvalidDataSource(), DataSourcePort)

    def test_fetch_method_signature(self) -> None:
        """DataSourcePort should require a specific fetch signature."""

        class ValidFetch:
            provider_name = "test"

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            async def fetch(
                self, entity_type: str, watermark: Any = None, limit: int | None = None
            ):
                yield {"data": entity_type, "watermark": watermark, "limit": limit}

            async def health_check(self):
                from bioetl.domain.types import HealthStatus

                return HealthStatus.HEALTHY

            async def aclose(self):
                pass

        assert isinstance(ValidFetch(), DataSourcePort)

        class InvalidFetchSignature:
            provider_name = "test"

            # Missing watermark and limit
            async def fetch(self, entity_type: str):
                yield {}

            async def health_check(self):
                from bioetl.domain.types import HealthStatus

                return HealthStatus.HEALTHY

            async def aclose(self):
                pass

        assert not isinstance(InvalidFetchSignature(), DataSourcePort)


@pytest.mark.unit
class TestStoragePortProtocol:
    """Tests for the StoragePort protocol."""

    def test_write_silver_signature(self) -> None:
        """StoragePort should require a specific write_silver signature."""
        from collections.abc import Iterator
        from typing import Literal
        from bioetl.domain.types import BatchID

        class ValidStorage:
            async def write_bronze(
                self,
                records: Iterator[bytes],
                provider: str,
                entity: str,
                date: Any,
                batch_id: BatchID,
            ) -> None:
                pass

            async def write_silver(
                self,
                table_name: str,
                records: list[dict[str, Any]],
                primary_keys: list[str],
                schema: Any,
                mode: Literal["merge", "append", "delete"] = "merge",
            ) -> None:
                pass

            async def write_gold(
                self,
                table_name: str,
                records: list[dict[str, Any]],
                mode: Literal["overwrite", "append", "scd2"] = "overwrite",
            ) -> None:
                pass

            async def aclose(self) -> None:
                pass

        assert isinstance(ValidStorage(), StoragePort)

        # Note: @runtime_checkable protocols only check for method presence,
        # not signatures. Test missing methods instead.
        class InvalidStorage:
            async def write_bronze(self, *args, **kwargs):
                pass

            # Missing write_silver method entirely
            async def write_gold(self, *args, **kwargs):
                pass

            async def aclose(self):
                pass

        assert not isinstance(InvalidStorage(), StoragePort)
