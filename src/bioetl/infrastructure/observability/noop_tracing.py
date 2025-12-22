"""No-op implementation of TracingPort."""

from typing import Any

class NoOpTracer:
    """No-op tracer that does nothing."""
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass
    def start_as_current_span(self, name: str): return self
    def set_attribute(self, key: str, value: Any): pass
    def set_status(self, status: Any): pass
    def record_exception(self, exception: Exception): pass


class NoOpTracing:
    """No-op implementation of TracingPort."""

    def get_tracer(self, name: str) -> Any:
        return NoOpTracer()
