"""Tests for domain ports (Protocol interfaces)."""

import pytest

from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    LockPort,
    QuarantinePort,
    StoragePort,
)


class TestPortsAreRuntimeCheckable:
    """Verify that all ports are @runtime_checkable."""

    @pytest.mark.parametrize(
        "port",
        [
            DataSourcePort,
            StoragePort,
            LockPort,
            CheckpointPort,
            QuarantinePort,
        ],
    )
    def test_port_is_runtime_checkable(self, port: type) -> None:
        """Each port should have _is_runtime_protocol attribute."""
        assert hasattr(port, "_is_runtime_protocol"), (
            f"{port.__name__} is not runtime checkable. "
            "Add @runtime_checkable decorator."
        )


class TestDataSourcePortProtocol:
    """Tests for DataSourcePort protocol compliance."""

    def test_provider_name_attribute_required(self) -> None:
        """DataSourcePort should require provider_name attribute."""

        class ValidDataSource:
            provider_name = "test"

            async def fetch(self, _entity_type, _watermark=None, _limit=None):
                yield {}

            async def health_check(self):
                from bioetl.domain.types import HealthStatus

                return HealthStatus.HEALTHY

        # Should pass isinstance check
        assert isinstance(ValidDataSource(), DataSourcePort)

    def test_missing_provider_name_fails_check(self) -> None:
        """Class without provider_name should not be DataSourcePort."""

        class InvalidDataSource:
            async def fetch(self, _entity_type, _watermark=None, _limit=None):
                yield {}

            async def health_check(self):
                from bioetl.domain.types import HealthStatus

                return HealthStatus.HEALTHY

        # Should fail isinstance check
        assert not isinstance(InvalidDataSource(), DataSourcePort)


class TestStoragePortProtocol:
    """Tests for StoragePort protocol compliance."""

    def test_valid_storage_passes_check(self) -> None:
        """Class with all required methods should be StoragePort."""

        class ValidStorage:
            def write_bronze(self, _records, _provider, _entity, _date, _batch_id):
                pass

            def write_silver(self, _table_name, _records, _primary_keys, _mode="merge"):
                pass

            def write_gold(self, _table_name, _records, _mode="overwrite"):
                pass

        assert isinstance(ValidStorage(), StoragePort)

    def test_missing_method_fails_check(self) -> None:
        """Class missing a required method should not be StoragePort."""

        class IncompleteStorage:
            def write_bronze(self, _records, _provider, _entity, _date, _batch_id):
                pass

            def write_silver(self, _table_name, _records, _primary_keys, _mode="merge"):
                pass

            # Missing write_gold

        assert not isinstance(IncompleteStorage(), StoragePort)


class TestLockPortProtocol:
    """Tests for LockPort protocol compliance."""

    def test_valid_lock_passes_check(self) -> None:
        """Class with all required methods should be LockPort."""

        class ValidLock:
            async def acquire(
                self,
                _key,
                _owner_id,
                _ttl=None,
                _wait=False,
                _wait_timeout=300,
                _exclusive=False,
            ):
                return True

            async def release(self, _key, _owner_id, _exclusive=False):
                return True

            async def heartbeat(self, _key, _owner_id, _exclusive=False):
                return True

        assert isinstance(ValidLock(), LockPort)


class TestCheckpointPortProtocol:
    """Tests for CheckpointPort protocol compliance."""

    def test_valid_checkpoint_passes_check(self) -> None:
        """Class with all required methods should be CheckpointPort."""

        class ValidCheckpoint:
            def save(self, _pipeline, _watermark, _run_id, _metadata):
                pass

            def load(self, _pipeline):
                return None

            def list_all(self):
                return []

            def delete(self, _pipeline):
                pass

        assert isinstance(ValidCheckpoint(), CheckpointPort)


class TestQuarantinePortProtocol:
    """Tests for QuarantinePort protocol compliance."""

    def test_valid_quarantine_passes_check(self) -> None:
        """Class with all required methods should be QuarantinePort."""

        class ValidQuarantine:
            def write(
                self,
                _pipeline,
                _error_code,
                _payload,
                _bronze_batch_id,
                *_args,
                **_kwargs,
            ):
                pass

            def inspect(self, _pipeline, _limit=10, _error_code=None):
                return []

            def get_stats(self, _pipeline):
                return {}

        assert isinstance(ValidQuarantine(), QuarantinePort)
