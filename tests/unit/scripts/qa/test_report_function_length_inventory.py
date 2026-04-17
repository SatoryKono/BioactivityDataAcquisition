from __future__ import annotations

from pathlib import Path

from scripts.engineering.qa.report_function_length_inventory import _build_payload
from scripts.engineering.qa.report_function_length_inventory import _render_markdown
from scripts.engineering.qa.report_function_length_inventory import (
    _scan_near_threshold_functions,
)
from scripts.engineering.qa.report_function_length_inventory import FunctionLengthEntry


def test_scan_near_threshold_functions_returns_sorted_entries(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()
    module_path = source_root / "sample.py"
    module_path.write_text(
        "\n".join(
            [
                "def short():",
                "    return 1",
                "",
                "def long_one():",
                *["    x = 1" for _ in range(84)],
                "    return x",
                "",
                "def long_two():",
                *["    y = 2" for _ in range(88)],
                "    return y",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    entries = _scan_near_threshold_functions(
        src_root=source_root,
        warn_threshold=80,
        max_lines=100,
    )

    assert [entry.symbol for entry in entries] == ["long_two", "long_one"]
    assert all(80 <= entry.length <= 100 for entry in entries)


def test_build_payload_reports_counts_and_entries() -> None:
    entries = [
        FunctionLengthEntry(
            path="src/bioetl/application/foo.py",
            symbol="build_foo",
            line=12,
            length=91,
        )
    ]

    payload = _build_payload(
        src_root=Path("src/bioetl"),
        warn_threshold=80,
        max_lines=100,
        entries=entries,
    )

    assert payload["mode"] == "report-only"
    assert payload["near_threshold_count"] == 1
    assert payload["entries"] == [
        {
            "path": "src/bioetl/application/foo.py",
            "symbol": "build_foo",
            "line": 12,
            "length": 91,
        }
    ]


def test_render_markdown_includes_summary_and_limit_notice() -> None:
    entries = [
        FunctionLengthEntry(
            path="src/bioetl/application/foo.py",
            symbol="build_foo",
            line=12,
            length=91,
        ),
        FunctionLengthEntry(
            path="src/bioetl/application/bar.py",
            symbol="build_bar",
            line=30,
            length=88,
        ),
    ]

    markdown = _render_markdown(
        src_root=Path("src/bioetl"),
        warn_threshold=80,
        max_lines=100,
        entries=entries,
        limit=1,
    )

    assert "# Function Length Inventory" in markdown
    assert "mode: report-only" in markdown
    assert "near_threshold_count: `2`" in markdown
    assert "`src/bioetl/application/foo.py:12`" in markdown
    assert "Showing top `1` entries out of `2`." in markdown
