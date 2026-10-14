"""Preserve every pytest subtest as a distinct JUnit testcase.

The pinned pytest reporter counts subtest reports but reuses their parent's
node reporter. Give only the XML writer a separate report identity; pytest's
failure propagation and the strict downstream JUnit accounting stay intact.
"""

from __future__ import annotations

import copy
from collections import Counter

import pytest
from _pytest.junitxml import LogXML, xml_key
from _pytest.reports import TestReport
from _pytest.subtests import SubtestReport


class _SubtestLogXML(LogXML):
    subtest_counts: Counter[tuple[str, str | None]]

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        if not isinstance(report, SubtestReport):
            super().pytest_runtest_logreport(report)
            return
        # Copy rather than mutate: the subtests plugin needs the original
        # parent nodeid to propagate a failed child to the parent test.
        child = copy.copy(report)
        key = (report.nodeid, getattr(report, "worker_id", None))
        self.subtest_counts[key] += 1
        child.nodeid = f"{report.nodeid} [subtest {self.subtest_counts[key]}]"
        super().pytest_runtest_logreport(child)
        self.finalize(child)
        if child in self.open_reports:
            self.open_reports.remove(child)


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    """Replace the pinned XML reporter only when JUnit output is requested."""
    original = config.stash.get(xml_key, None)
    if original is None or isinstance(original, _SubtestLogXML):
        return
    replacement = _SubtestLogXML(
        original.logfile,
        original.prefix,
        original.suite_name,
        original.logging,
        original.report_duration,
        original.family,
        original.log_passing_tests,
    )
    replacement.subtest_counts = Counter()
    replacement.global_properties = original.global_properties
    config.pluginmanager.unregister(original)
    config.stash[xml_key] = replacement
    config.pluginmanager.register(replacement)
