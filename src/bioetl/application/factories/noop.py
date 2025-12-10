"""No-op (stub) factory functions for testing and fallback scenarios."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from bioetl.domain.observability import MetricsPortABC


def create_noop_metrics_port() -> MetricsPortABC:
    """Return metrics port that records nothing (for tests/fallback)."""

    return cast(
        MetricsPortABC,
        SimpleNamespace(
            inc_counter=lambda *_args, **_kwargs: None,
            observe_histogram=lambda *_args, **_kwargs: None,
            update_stage_duration=lambda **_kwargs: None,
            update_stage_total=lambda **_kwargs: None,
        ),
    )
