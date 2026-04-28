"""Architecture tests for governance freshness protocol markers."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_doc_publication_policy_documents_freshness_protocol() -> None:
    text = _read("docs/00-project/governance/06-doc-publication-policy.md")
    lower_text = text.lower()

    assert "## Freshness Protocol" in text
    assert "generated artifacts" in lower_text
    assert "summaries" in lower_text
    assert "dated reports" in lower_text
    assert "python -m scripts.docs check-drift --freshness" in text


def test_plans_index_documents_refresh_triggers() -> None:
    text = _read("docs/plans/README.md")

    assert "## Freshness Triggers" in text
    assert "Freshness note" in text
    assert "reports/plans/" in text


def test_evidence_index_declares_rebaseline_model() -> None:
    text = _read("docs/reports/evidence/INDEX.md").lower()

    assert "freshness model" in text
    assert "rebaseline" in text
    assert "historical" in text


def test_high_signal_reports_carry_freshness_notes() -> None:
    candidate_paths = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "docs" / "plans").glob("*2026-*.md"))
    ]
    assert candidate_paths, "Expected at least one high-signal dated report artifact"

    paths_with_freshness_note = []
    for relative_path in candidate_paths:
        text = _read(relative_path)
        if "Freshness note" in text:
            paths_with_freshness_note.append(relative_path)

    assert paths_with_freshness_note, (
        "Expected at least one high-signal dated report artifact with a Freshness note"
    )


def test_technical_debt_surfaces_mark_rebaseline_status() -> None:
    for relative_path in (
        "docs/reports/evidence/technical-debt/SUMMARY.md",
        "docs/reports/evidence/technical-debt/complexity-hotspots/SUMMARY.md",
        "docs/reports/evidence/technical-debt/03-synthesis/CROSS-SYNTHESIS.md",
    ):
        text = _read(relative_path).lower()
        assert "rebaseline" in text or "historical trigger evidence" in text, (
            f"{relative_path} is missing rebaseline guidance"
        )
