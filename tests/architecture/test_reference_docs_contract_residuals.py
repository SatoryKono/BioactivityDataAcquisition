"""Fail-closed contracts for #9002 reference-docs residuals."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_openalex_publication_type_is_defined_once() -> None:
    text = _read("docs/04-reference/providers/openalex/publication.md")
    assert text.count("| `publication_type`") == 1
    assert "publication_type_raw" not in text
    assert '"publication_type": "article"' in text


def test_chembl_schema_pages_are_not_placeholders() -> None:
    pages = (
        "docs/04-reference/schemas/domain/chembl/activity-schema.md",
        "docs/04-reference/schemas/domain/chembl/assay-schema.md",
        "docs/04-reference/schemas/domain/chembl/target-schema.md",
    )
    for relative in pages:
        text = _read(relative)
        assert "Placeholder content" not in text
        assert "chembl_" in text
        assert "Gold contract:" in text
        gold_name = {
            "activity-schema.md": "chembl_activity_v1.0.json",
            "assay-schema.md": "chembl_assay_v1.0.json",
            "target-schema.md": "chembl_target_v3.0.json",
        }[Path(relative).name]
        assert gold_name in text
        assert (ROOT / "docs/04-reference/contracts/gold" / gold_name).is_file()
