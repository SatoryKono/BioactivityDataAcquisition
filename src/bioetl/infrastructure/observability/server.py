"""Prometheus metrics HTTP server.

This module provides a metrics server manager for Prometheus metrics,
ensuring only one metrics server is started per process.

Architecture notes:
    - MetricsServerManager uses instance-level state for testability
    - A module-level factory function provides the default instance
    - For testing, create new instances or use reset_default_manager()
"""

from __future__ import annotations

from threading import Lock

from prometheus_client import start_http_server


class MetricsServerManager:
    """Manages the lifecycle of the Prometheus metrics HTTP server.

    This class uses instance-level state to allow for testing isolation.
    Each instance tracks its own started state independently.

    For production use, obtain the default instance via get_default_manager()
    or use the convenience function start_metrics_server_once().

    Example:
        # Production usage
        >>> started = start_metrics_server_once(enabled=True, port=8000, address="0.0.0.0")

        # Testing with isolated instance
        >>> manager = MetricsServerManager()
        >>> manager.start(enabled=True, port=9000, address="127.0.0.1")
    """

    def __init__(self) -> None:
        """Initialize a new MetricsServerManager instance."""
        self._started: bool = False
        self._lock: Lock = Lock()

    def start(self, *, enabled: bool, port: int, address: str) -> bool:
        """Start metrics HTTP server once per manager instance.

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

        with self._lock:
            if self._started:
                return False

            start_http_server(port, addr=address)
            self._started = True
            return True

    def is_started(self) -> bool:
        """Check if the metrics server has been started.

        Returns:
            True if server is running, False otherwise.
        """
        return self._started

    def reset(self) -> None:
        """Reset the server state (for testing only).

        Warning:
            This does not actually stop the HTTP server (Prometheus client
            doesn't support that). It only resets the internal flag.
            Use only in tests with process isolation.
        """
        with self._lock:
            self._started = False


# =============================================================================
# Default instance management
# =============================================================================

_default_manager: MetricsServerManager | None = None
_default_manager_lock: Lock = Lock()


def get_default_manager() -> MetricsServerManager:
    """Get or create the default MetricsServerManager instance.

    This function provides lazy initialization of the default manager.
    The instance is shared across the process for production use.

    Returns:
        The default MetricsServerManager instance.
    """
    global _default_manager
    if _default_manager is None:
        with _default_manager_lock:
            if _default_manager is None:
                _default_manager = MetricsServerManager()
    return _default_manager


def reset_default_manager() -> None:
    """Reset the default manager (for testing only).

    This resets the default manager's state and clears the cached instance.
    Use this in tests to ensure isolation between test cases.

    Warning:
        This does not stop the HTTP server if it was started.
    """
    global _default_manager
    with _default_manager_lock:
        if _default_manager is not None:
            _default_manager.reset()
        _default_manager = None


def create_metrics_server_manager() -> MetricsServerManager:
    """Factory function for creating a new MetricsServerManager instance.

    Use this for dependency injection or when you need an isolated instance.

    Returns:
        A new MetricsServerManager instance.

    Example:
        >>> manager = create_metrics_server_manager()
        >>> manager.start(enabled=True, port=8000, address="0.0.0.0")
    """
    return MetricsServerManager()


# =============================================================================
# Convenience functions (backward compatible API)
# =============================================================================


def start_metrics_server_once(*, enabled: bool, port: int, address: str) -> bool:
    """Start metrics HTTP server once per process.

    This is a convenience function that uses the default manager instance.

    Args:
        enabled: Whether metrics server should be started.
        port: Port number for the HTTP server.
        address: Address to bind the server to.

    Returns:
        True if server was started in this call,
        False if already running or disabled.
    """
    return get_default_manager().start(enabled=enabled, port=port, address=address)


__all__ = [
    "MetricsServerManager",
    "create_metrics_server_manager",
    "get_default_manager",
    "reset_default_manager",
    "start_metrics_server_once",
]
