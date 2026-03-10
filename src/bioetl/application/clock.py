"""Application-level default clock adapter."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.context import _now_utc
from bioetl.domain.ports import ClockPort


class DefaultClock(ClockPort):
    """Default app clock backed by domain UTC helper."""

    def now_utc(self) -> datetime:
        return _now_utc()
