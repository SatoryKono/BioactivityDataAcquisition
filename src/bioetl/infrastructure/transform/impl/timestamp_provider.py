"""Infrastructure implementation of TimestampProvider."""

from __future__ import annotations

from datetime import datetime, timezone

from bioetl.domain.transform.contracts import TimestampProviderABC


class DeterministicTimestampProvider(TimestampProviderABC):
    """
    Провайдер детерминированных временных меток.

    Фиксирует время при инициализации и возвращает его при всех вызовах.
    Это обеспечивает детерминизм в рамках одной сессии обработки данных.
    """

    def __init__(self, fixed_time: datetime | None = None) -> None:
        """
        Args:
            fixed_time: Фиксированное время. Если не указано,
                        используется текущее время (UTC).
        """
        if fixed_time is None:
            self._time = datetime.now(timezone.utc)
        else:
            # Ensure timezone awareness
            if fixed_time.tzinfo is None:
                self._time = fixed_time.replace(tzinfo=timezone.utc)
            else:
                self._time = fixed_time

    def get_extraction_timestamp(self) -> datetime:
        """Возвращает зафиксированный timestamp извлечения данных."""
        return self._time


__all__ = ["DeterministicTimestampProvider"]
