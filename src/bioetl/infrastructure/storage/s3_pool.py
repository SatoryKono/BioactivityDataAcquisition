"""Thread-safe S3 client pool for connection reuse.

Implements connection pooling to reduce resource consumption when
multiple components need S3 access.

Architecture:
- Singleton pattern with class-level instance cache
- Thread-safe access using threading.Lock
- Configurable max_pool_connections for boto3
- Cache key based on (endpoint_url, region) tuple
"""

from __future__ import annotations

import threading
from typing import Any, ClassVar

import boto3
from botocore.config import Config


class S3ClientPool:
    """Thread-safe S3 client pool for connection reuse.

    Maintains a pool of S3 clients keyed by (endpoint_url, region).
    Clients are reused across multiple components to reduce resource
    consumption and improve performance.

    Example:
        >>> client = S3ClientPool.get_client(
        ...     endpoint_url="http://localhost:9000",
        ...     region="us-east-1",
        ...     access_key="bioetl",
        ...     secret_key="bioetl_minio_pass",
        ... )
        >>> client.list_buckets()

    Thread Safety:
        All operations are protected by a threading.Lock to ensure
        safe concurrent access from multiple threads.

    Note:
        Credentials are only used when creating a new client for a
        given (endpoint_url, region) key. If a client already exists
        for that key, the cached client is returned regardless of
        credentials provided.
    """

    _instances: ClassVar[dict[tuple[str | None, str], Any]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def get_client(
        cls,
        endpoint_url: str | None,
        region: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        max_pool_connections: int = 50,
    ) -> Any:
        """Get or create an S3 client from the pool.

        Args:
            endpoint_url: S3 endpoint URL (for MinIO, e.g., 'http://localhost:9000')
            region: AWS region (e.g., 'us-east-1')
            access_key: AWS access key ID (optional, uses env vars if None)
            secret_key: AWS secret access key (optional, uses env vars if None)
            max_pool_connections: Maximum number of connections in the pool (default: 50)

        Returns:
            boto3 S3 client instance

        Example:
            >>> client = S3ClientPool.get_client(
            ...     endpoint_url="http://localhost:9000",
            ...     region="us-east-1",
            ... )
        """
        key = (endpoint_url, region)

        with cls._lock:
            if key not in cls._instances:
                session = boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region,
                )
                cls._instances[key] = session.client(
                    "s3",
                    endpoint_url=endpoint_url,
                    config=Config(
                        signature_version="s3v4",
                        max_pool_connections=max_pool_connections,
                    ),
                )
            return cls._instances[key]

    @classmethod
    def clear_pool(cls) -> None:
        """Clear all cached clients.

        Useful for testing or when credentials need to be refreshed.
        After calling this method, subsequent get_client() calls will
        create new client instances.

        Example:
            >>> S3ClientPool.clear_pool()  # Reset for testing
        """
        with cls._lock:
            cls._instances.clear()

    @classmethod
    def pool_size(cls) -> int:
        """Return the number of cached clients.

        Returns:
            Number of S3 clients currently in the pool

        Example:
            >>> size = S3ClientPool.pool_size()
            >>> print(f"Pool contains {size} clients")
        """
        with cls._lock:
            return len(cls._instances)
