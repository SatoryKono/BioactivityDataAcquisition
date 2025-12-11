from __future__ import annotations

from tools.check_registry_sync import build_sync_report


def test_registry_and_docs_are_in_sync() -> None:
    report = build_sync_report()
    assert not report.has_issues, report.render()
