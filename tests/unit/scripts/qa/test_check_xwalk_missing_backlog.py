"""Tests for the xwalk MISSING_* backlog guardrail."""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.qa.check_xwalk_missing_backlog import (
    _build_payload,
    collect_xwalk_missing_findings,
    validate_backlog,
)


def _write_xwalk(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _write_backlog(path: Path, *, xwalk_path: Path, fields: list[str]) -> Path:
    fields_yaml = "\n".join(f"          - {field}" for field in fields)
    path.write_text(
        f"""version: 1
scope: test
marker_kinds:
  - MISSING_CODE
  - MISSING_DOC
  - MISSING_GOLD
  - MISSING_TRANSFORMER
classification_values:
  - must_fix
  - should_fix
  - deferred
rules:
  - path: {xwalk_path.resolve().as_posix()}
    markers:
      MISSING_CODE:
        classification: must_fix
        owner_issue: 3213
        rationale: Test backlog entry.
        fields:
{fields_yaml}
""",
        encoding="utf-8",
    )
    return path


def test_collect_xwalk_missing_findings_detects_known_marker_kinds(
    tmp_path: Path,
) -> None:
    root = tmp_path / "docs/04-reference/pipelines"
    xwalk = _write_xwalk(
        root / "openalex/publication-xwalk.csv",
        """field,doc_spec,notes
title,OK,OK
grants,MISSING,MISSING_DOC
deprecated_alias,OK,MISSING_CODE;MISSING_TRANSFORMER
plain_missing,MISSING,OK
""",
    )

    findings = collect_xwalk_missing_findings(root)

    assert [(item.field, item.marker) for item in findings] == [
        ("deprecated_alias", "MISSING_CODE"),
        ("deprecated_alias", "MISSING_TRANSFORMER"),
        ("grants", "MISSING_DOC"),
    ]
    assert {item.provider for item in findings} == {"openalex"}
    assert {item.entity for item in findings} == {"publication"}
    assert {item.path for item in findings} == {xwalk.resolve().as_posix()}


def test_validate_backlog_accepts_matching_rule_fields(tmp_path: Path) -> None:
    root = tmp_path / "docs/04-reference/pipelines"
    xwalk = _write_xwalk(
        root / "chembl/activity-xwalk.csv",
        """field,notes
publication_doi,MISSING_CODE
""",
    )
    backlog = _write_backlog(
        tmp_path / "backlog.yaml",
        xwalk_path=xwalk,
        fields=["publication_doi"],
    )

    validation = validate_backlog(xwalk_root=root, backlog_path=backlog)

    assert validation.ok
    payload = _build_payload(validation)
    assert payload["missing_marker_count"] == 1
    assert payload["marker_counts"] == {"MISSING_CODE": 1}


def test_validate_backlog_rejects_new_field_for_existing_marker(
    tmp_path: Path,
) -> None:
    root = tmp_path / "docs/04-reference/pipelines"
    xwalk = _write_xwalk(
        root / "chembl/activity-xwalk.csv",
        """field,notes
publication_doi,MISSING_CODE
publication_pmid,MISSING_CODE
""",
    )
    backlog = _write_backlog(
        tmp_path / "backlog.yaml",
        xwalk_path=xwalk,
        fields=["publication_doi"],
    )

    validation = validate_backlog(xwalk_root=root, backlog_path=backlog)

    assert not validation.ok
    assert "New unclassified MISSING_CODE" in "\n".join(validation.errors)
    assert "publication_pmid" in "\n".join(validation.errors)


def test_validate_backlog_rejects_stale_backlog_field(tmp_path: Path) -> None:
    root = tmp_path / "docs/04-reference/pipelines"
    xwalk = _write_xwalk(
        root / "chembl/activity-xwalk.csv",
        """field,notes
publication_doi,MISSING_CODE
""",
    )
    backlog = _write_backlog(
        tmp_path / "backlog.yaml",
        xwalk_path=xwalk,
        fields=["publication_doi", "publication_pmid"],
    )

    validation = validate_backlog(xwalk_root=root, backlog_path=backlog)

    assert not validation.ok
    assert "Resolved MISSING_CODE still listed" in "\n".join(validation.errors)
    assert "publication_pmid" in "\n".join(validation.errors)


def test_current_repository_backlog_matches_xwalks() -> None:
    validation = validate_backlog()

    assert validation.ok
    payload = _build_payload(validation)
    assert payload["missing_marker_count"] == 214
    assert payload["marker_counts"] == {
        "MISSING_CODE": 2,
        "MISSING_DOC": 174,
        "MISSING_GOLD": 38,
    }
