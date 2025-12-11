"""Prometheus metrics HTTP server.

This module provides a singleton-pattern HTTP server for Prometheus metrics,
ensuring only one metrics server is started per process.
"""

from __future__ import annotations

from threading import Lock

from prometheus_client import start_http_server


class MetricsServerManager:
    """Manages the lifecycle of the Prometheus metrics HTTP server.

    This class encapsulates the global state needed to ensure only one
    metrics server is started per process. It is thread-safe.

    Example:
        >>> manager = MetricsServerManager()
        >>> started = manager.start(enabled=True, port=8000, address="0.0.0.0")
        >>> print(f"Server started: {started}")
    """

    _started: bool = False
    _lock: Lock = Lock()

    @classmethod
    def start(cls, *, enabled: bool, port: int, address: str) -> bool:
        """Start metrics HTTP server once per process.

        Args:
            enabled: Whether metrics server should be started.
            port: Port number for the HTTP server.
            address: Address to bind the server to.

        Returns:
            True if server was started in this call,
            False if already running or disabled.
        """
        if not enabled:
            return False

        with cls._lock:
            if cls._started:
                return False

            start_http_server(port, addr=address)
            cls._started = True
            return True

    @classmethod
    def is_started(cls) -> bool:
        """Check if the metrics server has been started.

        Returns:
            True if server is running, False otherwise.
        """
        return cls._started

    @classmethod
    def reset(cls) -> None:
        """Reset the server state (for testing only).

        Warning:
            This does not actually stop the HTTP server (Prometheus client
            doesn't support that). It only resets the internal flag.
            Use only in tests with process isolation.
        """
        cls._started = False


def start_metrics_server_once(*, enabled: bool, port: int, address: str) -> bool:
    """Start metrics HTTP server once per process.

    This is a convenience function that delegates to MetricsServerManager.

    Args:
        enabled: Whether metrics server should be started.
        port: Port number for the HTTP server.
        address: Address to bind the server to.

    Returns:
        True if server was started in this call,
        False if already running or disabled.
    """
    return MetricsServerManager.start(enabled=enabled, port=port, address=address)


__all__ = [
    "MetricsServerManager",
    "start_metrics_server_once",
]
