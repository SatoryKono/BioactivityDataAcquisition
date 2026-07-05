"""Unit tests for ADR metadata extraction helpers."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adr import _adr_metadata_extractors as extractors

pytestmark = pytest.mark.unit


def test_parse_h1_title_returns_first_h1_or_none() -> None:
    assert extractors.parse_h1_title("intro\n# ADR-001 Title\n## Not title") == (
        "ADR-001 Title"
    )
    assert extractors.parse_h1_title("## Only second-level") is None


def test_extract_prefixed_line_value_handles_bold_plain_and_empty_values() -> None:
    labels = tuple(label.casefold() for label in ("Status", "Date"))

    assert (
        extractors.extract_prefixed_line_value(
            "**Status:** Accepted",
            "**status:** accepted",
            labels,
        )
        == "Accepted"
    )
    assert (
        extractors.extract_prefixed_line_value(
            "Date: 2026-07-05",
            "date: 2026-07-05",
            labels,
        )
        == "2026-07-05"
    )
    assert extractors.extract_prefixed_line_value("Status:", "status:", labels) is None
    assert (
        extractors.extract_prefixed_line_value("Owner: team", "owner: team", labels)
        is None
    )


def test_extract_table_line_value_handles_shape_header_and_empty_cells() -> None:
    labels = tuple(label.casefold() for label in ("Status", "Date"))

    assert extractors.extract_table_line_value("Status | Accepted", labels) is None
    assert extractors.extract_table_line_value("| Status | Accepted |", labels) == (
        "Accepted"
    )
    assert (
        extractors.extract_table_line_value("| **Date** | 2026-07-05 |", labels)
        == "2026-07-05"
    )
    assert extractors.extract_table_line_value("| Status |", labels) is None
    assert extractors.extract_table_line_value("| Owner | Team |", labels) is None


def test_extract_labeled_line_value_skips_blank_lines_and_uses_first_match() -> None:
    text = "\n\nOwner: Team\n| Status | Accepted |\nStatus: Superseded"

    assert extractors.extract_labeled_line_value(text, ("Status",)) == "Accepted"
    assert extractors.extract_labeled_line_value(text, ("Date",)) is None
    assert extractors.extract_with_patterns("Date: 2026-07-05", ("Date",)) == (
        "2026-07-05"
    )


def test_first_content_line_stops_at_headings_tables_or_empty_window() -> None:
    assert extractors.first_content_line(["# Status", "", "Accepted"], 0) == "Accepted"
    assert extractors.first_content_line(["# Status", "## Next"], 0) is None
    assert (
        extractors.first_content_line(["# Status", "| Status | Accepted |"], 0) is None
    )
    assert (
        extractors.first_content_line(["# Status", "", "", "", "", "", "", ""], 0)
        is None
    )


def test_match_heading_to_section_exact_inline_and_non_matches() -> None:
    names = {"status", "date"}

    assert extractors.match_heading_to_section("Status", names) == (None, True)
    assert extractors.match_heading_to_section("Status: Accepted", names) == (
        "Accepted",
        False,
    )
    assert extractors.match_heading_to_section("Status:", names) == (None, False)
    assert extractors.match_heading_to_section("Owner", names) == (None, False)


def test_extract_from_section_handles_exact_inline_and_absent_sections() -> None:
    assert (
        extractors.extract_from_section(
            "# Status\n\nAccepted\n# Date\n2026-07-05", ("Status",)
        )
        == "Accepted"
    )
    assert (
        extractors.extract_from_section(
            "# Status: Accepted\n# Date\n2026-07-05", ("Status",)
        )
        == "Accepted"
    )
    assert (
        extractors.extract_from_section("# Status\n| Status | Accepted |", ("Status",))
        is None
    )
    assert extractors.extract_from_section("# Owner\nTeam", ("Status",)) is None


def test_extract_meta_prefers_labels_then_falls_back_to_sections() -> None:
    labeled = "# Title\n\n**Status:** Accepted\nDate: 2026-07-05"
    sectioned = "# Title\n\n## Status\nAccepted\n\n## Date: 2026-07-05"
    missing = "# Title\n\nNo metadata"

    assert extractors.extract_meta(labeled) == ("Accepted", "2026-07-05")
    assert extractors.extract_meta(sectioned) == ("Accepted", "2026-07-05")
    assert extractors.extract_meta(missing) == (None, None)
