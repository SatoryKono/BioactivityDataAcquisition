"""HTTP сервер экспонирования метрик Prometheus."""

from __future__ import annotations

from threading import Lock

from prometheus_client import start_http_server

_metrics_server_started = False
_metrics_server_lock = Lock()


def start_metrics_server_once(*, enabled: bool, port: int, address: str) -> bool:
    """Запускает HTTP сервер метрик один раз на процесс.

    Возвращает ``True``, если сервер был запущен в текущем вызове, и ``False``
    если он уже работал или отключен конфигурацией.
    """

    if not enabled:
        return False

    global _metrics_server_started
    with _metrics_server_lock:
        if _metrics_server_started:
            return False

        start_http_server(port, addr=address)
        _metrics_server_started = True
        return True


__all__ = ["start_metrics_server_once"]
