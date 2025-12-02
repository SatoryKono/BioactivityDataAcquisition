import random
import time

from bioetl.infrastructure.clients.base.contracts import RetryPolicyABC


class ExponentialBackoffRetryImpl(RetryPolicyABC):
    """
    Экспоненциальная задержка с Jitter.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ) -> None:
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._backoff_factor = backoff_factor
        self._jitter = jitter

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    def should_retry(self, error: Exception, attempt: int) -> bool:
        if attempt >= self._max_attempts:
            return False
        # В реальной реализации здесь была бы проверка типа ошибки
        return True

    def get_delay(self, attempt: int) -> float:
        delay = self._base_delay * (self._backoff_factor ** (attempt - 1))
        if self._jitter:
            delay *= random.uniform(0.5, 1.5)
        return min(delay, self._max_delay)

