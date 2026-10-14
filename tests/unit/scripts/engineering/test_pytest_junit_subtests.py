"""Real pytest subprocess regressions for subtest JUnit accounting."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

from scripts.engineering.ci.junit_duration_summary import derive_summary

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("outcome", ["pass", "fail", "skip"])
@pytest.mark.parametrize("parallel", [False, True])
def test_subtest_records_preserve_outcomes_and_exact_counts(
    tmp_path: Path, outcome: str, parallel: bool
) -> None:
    """Report all children without hiding a failed or skipped assertion."""
    source = tmp_path / "test_example.py"
    source.write_text(
        "import unittest\n"
        "class Example(unittest.TestCase):\n"
        "    def test_children(self):\n"
        "        for i in range(3):\n"
        "            with self.subTest(i=i):\n"
        f"                if i == 1 and {outcome!r} == 'skip':\n"
        "                    self.skipTest('explicit subtest skip')\n"
        f"                self.assertFalse(i == 1 and {outcome!r} == 'fail')\n",
        encoding="utf-8",
    )
    config = tmp_path / "pytest.ini"
    config.write_text("[pytest]\n", encoding="utf-8")
    junit = tmp_path / "junit.xml"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(config),
            "-p",
            "scripts.engineering.dev.pytest_junit_subtests",
            *(["-p", "xdist.plugin", "-n", "1"] if parallel else []),
            str(source),
            "-q",
            f"--junitxml={junit}",
        ],
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": ""},
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == (1 if outcome == "fail" else 0), (
        result.stdout + result.stderr
    )
    suite = ElementTree.parse(junit).getroot().find("testsuite")
    assert suite is not None
    cases = suite.findall("testcase")
    assert len(cases) == int(suite.attrib["tests"]) == 4
    assert len({case.attrib["name"] for case in cases}) == 4
    assert sum(case.find("skipped") is not None for case in cases) == (
        outcome == "skip"
    )
    failures = sum(case.find("failure") is not None for case in cases)
    assert failures == (1 if outcome == "fail" else 0)
    if outcome == "fail":
        failed = next(case for case in cases if case.find("failure") is not None)
        assert failed.attrib["name"].endswith("[subtest 2]")
    # Exercise the same strict consumer that rejected the original capture.
    derive_summary([junit])
