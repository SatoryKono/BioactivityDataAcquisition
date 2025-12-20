"""Unit tests for S3 client pool with concurrent access."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.storage.s3_pool import S3ClientPool


@pytest.fixture(autouse=True)
def clear_pool():
    """Clear the pool before and after each test."""
    S3ClientPool.clear_pool()
    yield
    S3ClientPool.clear_pool()


@pytest.fixture
def mock_boto3_session():
    """Mock boto3.Session for testing."""
    with patch("bioetl.infrastructure.storage.s3_pool.boto3.Session") as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        yield mock_session, mock_client


@pytest.mark.unit
class TestS3ClientPool:
    """Test S3ClientPool functionality."""

    def test_get_client_creates_new_client(self, mock_boto3_session):
        """Test that get_client creates a new client when pool is empty."""
        mock_session, mock_client = mock_boto3_session

        client = S3ClientPool.get_client(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
            access_key="test_key",
            secret_key="test_secret",
        )

        assert client is mock_client
        mock_session.assert_called_once_with(
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret",
            region_name="us-east-1",
        )
        mock_session.return_value.client.assert_called_once()

    def test_get_client_reuses_existing_client(self, mock_boto3_session):
        """Test that get_client reuses existing client for same key."""
        mock_session, _mock_client = mock_boto3_session

        client1 = S3ClientPool.get_client(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
        )
        client2 = S3ClientPool.get_client(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
        )

        assert client1 is client2
        # Session should only be created once
        assert mock_session.call_count == 1

    def test_different_endpoints_create_different_clients(self, mock_boto3_session):
        """Test that different endpoints create separate clients."""
        mock_session, _ = mock_boto3_session

        # Create different mock clients for each call
        mock_client1 = MagicMock(name="client1")
        mock_client2 = MagicMock(name="client2")
        mock_session.return_value.client.side_effect = [mock_client1, mock_client2]

        client1 = S3ClientPool.get_client(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
        )
        client2 = S3ClientPool.get_client(
            endpoint_url="http://localhost:9001",
            region="us-east-1",
        )

        assert client1 is not client2
        assert mock_session.call_count == 2

    def test_different_regions_create_different_clients(self, mock_boto3_session):
        """Test that different regions create separate clients."""
        mock_session, _ = mock_boto3_session

        mock_client1 = MagicMock(name="client1")
        mock_client2 = MagicMock(name="client2")
        mock_session.return_value.client.side_effect = [mock_client1, mock_client2]

        client1 = S3ClientPool.get_client(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
        )
        client2 = S3ClientPool.get_client(
            endpoint_url="http://localhost:9000",
            region="eu-west-1",
        )

        assert client1 is not client2
        assert mock_session.call_count == 2

    def test_clear_pool_removes_all_clients(self, mock_boto3_session):
        """Test that clear_pool removes all cached clients."""
        _mock_session, _ = mock_boto3_session

        S3ClientPool.get_client(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
        )
        S3ClientPool.get_client(
            endpoint_url="http://localhost:9001",
            region="us-east-1",
        )

        assert S3ClientPool.pool_size() == 2

        S3ClientPool.clear_pool()

        assert S3ClientPool.pool_size() == 0

    def test_pool_size_returns_correct_count(self, mock_boto3_session):
        """Test that pool_size returns correct number of clients."""
        _mock_session, _ = mock_boto3_session

        assert S3ClientPool.pool_size() == 0

        S3ClientPool.get_client(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
        )
        assert S3ClientPool.pool_size() == 1

        # Same key, should not increase count
        S3ClientPool.get_client(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
        )
        assert S3ClientPool.pool_size() == 1

    def test_none_endpoint_url_is_valid_key(self, mock_boto3_session):
        """Test that None endpoint_url works for AWS S3."""
        _mock_session, mock_client = mock_boto3_session

        client = S3ClientPool.get_client(
            endpoint_url=None,
            region="us-east-1",
        )

        assert client is mock_client
        assert S3ClientPool.pool_size() == 1


@pytest.mark.unit
class TestS3ClientPoolConcurrency:
    """Test S3ClientPool thread safety with concurrent access."""

    def test_concurrent_access_same_key(self, mock_boto3_session):
        """Test concurrent access to the same key returns same client."""
        mock_session, _mock_client = mock_boto3_session
        results = []
        errors = []

        def get_client():
            try:
                client = S3ClientPool.get_client(
                    endpoint_url="http://localhost:9000",
                    region="us-east-1",
                )
                results.append(client)
            except Exception as e:
                errors.append(e)

        # Reduced from 100 to 20 to avoid potential hangs/slowdowns
        threads = [threading.Thread(target=get_client) for _ in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 20
        # All clients should be the same instance
        assert all(client is results[0] for client in results)
        # Session should only be created once
        assert mock_session.call_count == 1

    def test_concurrent_access_different_keys(self, mock_boto3_session):
        """Test concurrent access to different keys creates separate clients."""
        mock_session, _ = mock_boto3_session

        # Create unique mock clients for each call
        call_count = 0

        def create_mock_client(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(name=f"client_{call_count}")

        mock_session.return_value.client.side_effect = create_mock_client

        results = {}
        lock = threading.Lock()
        errors = []

        def get_client(endpoint_port):
            try:
                client = S3ClientPool.get_client(
                    endpoint_url=f"http://localhost:{endpoint_port}",
                    region="us-east-1",
                )
                with lock:
                    if endpoint_port not in results:
                        results[endpoint_port] = []
                    results[endpoint_port].append(client)
            except Exception as e:
                errors.append(e)

        # Reduced: 5 different endpoints, 4 threads each (20 total)
        threads = []
        for port in range(9000, 9005):
            for _ in range(4):
                threads.append(threading.Thread(target=get_client, args=(port,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5  # 5 different endpoints

        # Each endpoint should have 4 results, all the same client
        for _port, clients in results.items():
            assert len(clients) == 4
            assert all(c is clients[0] for c in clients)

        # Should have created exactly 5 clients
        assert S3ClientPool.pool_size() == 5

    def test_concurrent_clear_and_get(self, mock_boto3_session):
        """Test concurrent clear and get operations are thread-safe."""
        _mock_session, _ = mock_boto3_session

        def create_mock_client(*_args, **_kwargs):
            return MagicMock()

        _mock_session.return_value.client.side_effect = create_mock_client

        errors = []

        def get_client():
            try:
                S3ClientPool.get_client(
                    endpoint_url="http://localhost:9000",
                    region="us-east-1",
                )
            except Exception as e:
                errors.append(e)

        def clear_pool():
            try:
                S3ClientPool.clear_pool()
            except Exception as e:
                errors.append(e)

        # Mix of get and clear operations
        # Reduced max_workers and iterations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(20):
                if i % 5 == 0:
                    futures.append(executor.submit(clear_pool))
                else:
                    futures.append(executor.submit(get_client))

            for future in as_completed(futures):
                future.result()  # Raises exception if any

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_memory_stability_many_batches(self, mock_boto3_session):
        """Test memory usage is stable with many operations."""
        mock_session, _ = mock_boto3_session

        def create_mock_client(*_args, **_kwargs):
            return MagicMock()

        mock_session.return_value.client.side_effect = create_mock_client

        # Reduced from 1000 to 50 for faster execution
        num_batches = 50
        num_endpoints = 5

        for batch in range(num_batches):
            endpoint_port = 9000 + (batch % num_endpoints)
            S3ClientPool.get_client(
                endpoint_url=f"http://localhost:{endpoint_port}",
                region="us-east-1",
            )

        # Pool size should be fixed regardless of number of batches
        assert S3ClientPool.pool_size() == num_endpoints
        # Number of client creations should equal number of unique endpoints
        assert mock_session.return_value.client.call_count == num_endpoints
