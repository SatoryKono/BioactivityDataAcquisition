"""Unit tests for domain ports (Protocols)."""

from typing import Any

import pytest

from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    LockPort,
    MetricsPort,
    QuarantinePort,
    StoragePort,
)
from bioetl.domain.types import BatchID, RunID


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

            async def fetch(self, _entity_type, _limit=None, _query=None):
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
            async def fetch(self, _entity_type, _limit=None, _query=None):
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
                self, entity_type: str, limit: int | None = None, query: str | None = None
            ):
                yield {"data": entity_type, "limit": limit, "query": query}

            async def health_check(self):
                from bioetl.domain.types import HealthStatus

                return HealthStatus.HEALTHY

            async def aclose(self):
                pass

        assert isinstance(ValidFetch(), DataSourcePort)

        class InvalidFetchSignature:
            provider_name = "test"

            # Missing limit and query
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
                run_id: Any,
                run_type: Any,
            ) -> None:
                pass

            async def write_silver(
                self,
                table_name: str,
                records: list[dict[str, Any]],
                primary_keys: list[str],
                schema: Any,
                mode: Literal["merge", "append", "delete"] = "merge",
                partition_cols: list[str] | None = None,
            ) -> None:
                pass

            async def write_gold(
                self,
                table_name: str,
                records: list[dict[str, Any]],
                primary_keys: list[str] | None = None,
                mode: Literal["overwrite", "append", "scd2"] = "overwrite",
            ) -> None:
                pass

            async def aclose(self) -> None:
                pass

            async def clear_silver(
                self, table_name: str, dry_run: bool = False
            ) -> int:
                return 0

            async def clear_gold(
                self, table_name: str, dry_run: bool = False
            ) -> int:
                return 0

            async def clear_csv(self, table_name: str | None = None) -> int:
                return 0

            async def clear_delta(self, table_name: str | None = None) -> int:
                return 0

            def preview_cleanup(
                self,
                silver_table: str,
                gold_table: str | None = None,
            ) -> dict[str, Any]:
                return {}

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


@pytest.mark.unit
class TestLockPortProtocol:
    """Tests for the LockPort protocol."""

    def test_valid_lock_implementation(self) -> None:
        """LockPort should accept valid implementations."""

        class ValidLock:
            async def acquire(
                self,
                key: str,
                owner_id: RunID,
                ttl: int | None = None,
                wait: bool = False,
                wait_timeout: int = 300,
                exclusive: bool = False,
            ) -> bool:
                return True

            async def release(
                self,
                key: str,
                owner_id: RunID,
                exclusive: bool = False,
            ) -> bool:
                return True

            async def heartbeat(
                self,
                key: str,
                owner_id: RunID,
                exclusive: bool = False,
            ) -> bool:
                return True

            async def aclose(self) -> None:
                pass

        assert isinstance(ValidLock(), LockPort)

    def test_missing_method_fails(self) -> None:
        """LockPort should reject implementations missing methods."""

        class InvalidLock:
            async def acquire(self, key: str, owner_id: RunID) -> bool:
                return True

            # Missing release, heartbeat, aclose
            async def aclose(self) -> None:
                pass

        assert not isinstance(InvalidLock(), LockPort)


@pytest.mark.unit
class TestCheckpointPortProtocol:
    """Tests for the CheckpointPort protocol."""

    def test_valid_checkpoint_implementation(self) -> None:
        """CheckpointPort should accept valid implementations."""

        class ValidCheckpoint:
            async def save(
                self,
                pipeline: str,
                run_id: RunID,
                metadata: dict[str, Any],
            ) -> None:
                pass

            async def load(
                self,
                pipeline: str,
            ) -> tuple[RunID, dict[str, Any]] | None:
                return None

            async def list_all(self) -> list[str]:
                return []

            async def delete(self, pipeline: str) -> None:
                pass

            async def aclose(self) -> None:
                pass

        assert isinstance(ValidCheckpoint(), CheckpointPort)

    def test_missing_save_fails(self) -> None:
        """CheckpointPort should reject implementations missing save."""

        class InvalidCheckpoint:
            # Missing save method
            async def load(self, pipeline: str) -> None:
                return None

            async def list_all(self) -> list[str]:
                return []

            async def delete(self, pipeline: str) -> None:
                pass

            async def aclose(self) -> None:
                pass

        assert not isinstance(InvalidCheckpoint(), CheckpointPort)


@pytest.mark.unit
class TestQuarantinePortProtocol:
    """Tests for the QuarantinePort protocol."""

    def test_valid_quarantine_implementation(self) -> None:
        """QuarantinePort should accept valid implementations."""
        from bioetl.domain.types import RunID

        class ValidQuarantine:
            async def write(
                self,
                pipeline: str,
                error_code: str,
                payload: dict[str, Any],
                bronze_batch_id: BatchID,
                run_id: RunID | None = None,
                metadata: dict[str, Any] | None = None,
            ) -> None:
                pass

            async def inspect(
                self,
                pipeline: str,
                limit: int = 10,
                error_code: str | None = None,
            ) -> list[dict[str, Any]]:
                return []

            async def get_stats(self, pipeline: str) -> dict[str, Any]:
                return {}

            async def aclose(self) -> None:
                pass

        assert isinstance(ValidQuarantine(), QuarantinePort)

    def test_missing_write_fails(self) -> None:
        """QuarantinePort should reject implementations missing write."""

        class InvalidQuarantine:
            # Missing write method
            async def inspect(
                self,
                pipeline: str,
                limit: int = 10,
                error_code: str | None = None,
            ) -> list[dict[str, Any]]:
                return []

            async def get_stats(self, pipeline: str) -> dict[str, Any]:
                return {}

            async def aclose(self) -> None:
                pass

        assert not isinstance(InvalidQuarantine(), QuarantinePort)


@pytest.mark.unit
class TestMetricsPortProtocol:
    """Tests for the MetricsPort protocol."""

    def test_valid_metrics_implementation(self) -> None:
        """MetricsPort should accept valid implementations."""

        class ValidMetrics:
            def observe_histogram(
                self,
                name: str,
                value: float,
                labels: dict[str, str],
            ) -> None:
                pass

            def increment_counter(
                self,
                name: str,
                value: int,
                labels: dict[str, str],
            ) -> None:
                pass

            def set_gauge(
                self,
                name: str,
                value: float,
                labels: dict[str, str],
            ) -> None:
                pass

            def close(self) -> None:
                pass

        assert isinstance(ValidMetrics(), MetricsPort)

    def test_missing_observe_histogram_fails(self) -> None:
        """MetricsPort should reject implementations missing observe_histogram."""

        class InvalidMetrics:
            # Missing observe_histogram
            def increment_counter(
                self,
                name: str,
                value: int,
                labels: dict[str, str],
            ) -> None:
                pass

        assert not isinstance(InvalidMetrics(), MetricsPort)

    def test_missing_increment_counter_fails(self) -> None:
        """MetricsPort should reject implementations missing increment_counter."""

        class InvalidMetrics:
            def observe_histogram(
                self,
                name: str,
                value: float,
                labels: dict[str, str],
            ) -> None:
                pass

            # Missing increment_counter

        assert not isinstance(InvalidMetrics(), MetricsPort)
