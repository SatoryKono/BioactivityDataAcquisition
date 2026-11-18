"""Isolate the journal password inventory between CI architecture tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _reset_journal_blocked_inventory() -> Iterator[None]:
    from scripts.engineering.ci import pytest_event_journal as journal

    journal._clear_retained_blocked()
    yield
    journal._clear_retained_blocked()
