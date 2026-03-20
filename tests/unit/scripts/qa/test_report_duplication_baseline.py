from __future__ import annotations

from pathlib import Path

from scripts.qa.report_duplication_baseline import _parse_pylint_duplicate_output
from scripts.qa.report_duplication_baseline import _render_markdown
from scripts.qa.report_duplication_baseline import DuplicateCluster
from scripts.qa.report_duplication_baseline import DuplicateModuleRef
from scripts.qa.report_duplication_baseline import TargetDuplicationReport


def test_parse_pylint_duplicate_output_extracts_clusters() -> None:
    stdout = """
************* Module bioetl.application.foo
src\\bioetl\\application\\foo.py:10:0: R0801: Similar lines in 2 files
==bioetl.application.foo:[10:20]
==bioetl.application.bar:[30:40]
some duplicate text
src\\bioetl\\application\\baz.py:21:0: R0801: Similar lines in 2 files
==bioetl.application.baz:[21:28]
==bioetl.application.qux:[50:57]
""".strip()

    clusters = _parse_pylint_duplicate_output(stdout)

    assert len(clusters) == 2
    assert clusters[0].path == r"src\bioetl\application\foo.py"
    assert clusters[0].line == 10
    assert [m.module for m in clusters[0].modules] == [
        "bioetl.application.foo",
        "bioetl.application.bar",
    ]
    assert clusters[1].path == r"src\bioetl\application\baz.py"
    assert clusters[1].line == 21


def test_render_markdown_includes_targets_and_interpretation_note() -> None:
    report = TargetDuplicationReport(
        target="src/bioetl/application",
        returncode=8,
        duplicate_count=1,
        clusters=(
            DuplicateCluster(
                path="src/bioetl/application/foo.py",
                line=10,
                modules=(
                    DuplicateModuleRef(
                        module="bioetl.application.foo",
                        start_line=10,
                        end_line=20,
                    ),
                    DuplicateModuleRef(
                        module="bioetl.application.bar",
                        start_line=30,
                        end_line=40,
                    ),
                ),
            ),
        ),
    )

    markdown = _render_markdown([report])

    assert "# Duplication Baseline Report" in markdown
    assert "mode: report-only" in markdown
    assert "facades, export barrels, and compatibility shims" in markdown
    assert "`src/bioetl/application`" in markdown
    assert "`src/bioetl/application/foo.py:10`" in markdown
