"""Unit tests for docs KPI reporting safeguards."""

from __future__ import annotations

import pytest

from scripts.docs.checks import report_docs_kpi

pytestmark = pytest.mark.unit


class _BrokenStatPath:
    def is_file(self) -> bool:
        raise OSError(22, "Invalid argument")


class _BrokenReadPath:
    def read_text(self, *, encoding: str, errors: str) -> str:
        del encoding, errors
        raise OSError(22, "Invalid argument")


def test_docs_kpi_safe_is_file_returns_false_on_oserror() -> None:
    assert report_docs_kpi._safe_is_file(_BrokenStatPath()) is False  # type: ignore[arg-type]


def test_safe_read_text_returns_none_on_oserror() -> None:
    assert report_docs_kpi._safe_read_text(_BrokenReadPath()) is None  # type: ignore[arg-type]


def test_iter_inbound_targets_skips_unreadable_markdown() -> None:
    targets = report_docs_kpi._iter_inbound_targets(  # type: ignore[arg-type]
        _BrokenReadPath(),
        docs_root=report_docs_kpi.DOCS_DIR.resolve(),
    )

    assert targets == []
