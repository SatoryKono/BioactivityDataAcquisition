"""#11978: private-import waivers come from pair metadata, not comments."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts.engineering.qa.private_import_exception_metadata import (
    validate_exception_metadata,
)

pytestmark = pytest.mark.unit

_TODAY = date(2026, 10, 6)


def _pair(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "PIM-APP-001",
        "importer": "bioetl/application/example.py",
        "target": "bioetl.application._hidden",
        "owner": "@bioetl-application",
        "scope": "bioetl/application/example.py -> bioetl.application._hidden",
        "rationale": "Example helper still calls a private type contract owned by another module.",
        "sanction": "private-import ratchet #9626; no additional ADR waiver",
        "enforcement": "tests/architecture/test_private_module_imports.py",
        "classification": "temporary",
        "next_review": "2027-01-06",
        "exit_condition": "Move the shared types to a public module and delete this private import.",
        "target_removal_wave": "residual",
    }
    row.update(overrides)
    return row


def _config(*pairs: dict[str, object], **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "max_count": 11,
        "metadata_policy": {
            "classification_allowed": ["temporary"],
            "review_horizon_days": 120,
            "waiver_source": "yaml-pair-metadata",
        },
        "pairs": list(pairs),
    }
    payload.update(overrides)
    return payload


def test_valid_temporary_pair_is_accepted(tmp_path: Path) -> None:
    enforcement = tmp_path / "tests/architecture/test_private_module_imports.py"
    enforcement.parent.mkdir(parents=True)
    enforcement.write_text("# enforcement\n", encoding="utf-8")
    errors = validate_exception_metadata(
        _config(_pair()),
        project_root=tmp_path,
        today=_TODAY,
    )
    assert errors == []


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda row: row.pop("rationale"), "missing rationale"),
        (lambda row: row.update(id="EXC-002"), "unknown exception id"),
        (
            lambda row: row.update(
                scope="bioetl/application/*.py -> bioetl.application._hidden"
            ),
            "widened scope",
        ),
        (lambda row: row.update(next_review="2026-01-01"), "stale temporary review"),
        (lambda row: row.update(next_review="2027-06-01"), "outside the horizon"),
        (lambda row: row.update(classification="permanent"), "must be temporary"),
        (lambda row: row.update(exit_condition="residual"), "exit_condition"),
        (lambda row: row.update(owner="@unknown"), "unknown owner"),
    ],
)
def test_metadata_rejections(
    tmp_path: Path,
    mutate: object,
    fragment: str,
) -> None:
    enforcement = tmp_path / "tests/architecture/test_private_module_imports.py"
    enforcement.parent.mkdir(parents=True)
    enforcement.write_text("# enforcement\n", encoding="utf-8")
    row = _pair()
    assert callable(mutate)
    mutate(row)
    errors = validate_exception_metadata(
        _config(row),
        project_root=tmp_path,
        today=_TODAY,
    )
    assert any(fragment in error for error in errors), errors


def test_duplicate_id_and_over_cap_are_rejected(tmp_path: Path) -> None:
    enforcement = tmp_path / "tests/architecture/test_private_module_imports.py"
    enforcement.parent.mkdir(parents=True)
    enforcement.write_text("# enforcement\n", encoding="utf-8")
    errors = validate_exception_metadata(
        _config(_pair(), _pair(), max_count=12),
        project_root=tmp_path,
        today=_TODAY,
    )
    assert any("duplicate exception id" in error for error in errors)
    assert any("exceeds the #11978 ceiling" in error for error in errors)


def test_source_comment_does_not_create_a_waiver(tmp_path: Path) -> None:
    """Pair metadata is the only waiver source. A source comment adds no row."""
    enforcement = tmp_path / "tests/architecture/test_private_module_imports.py"
    enforcement.parent.mkdir(parents=True)
    enforcement.write_text("# enforcement\n", encoding="utf-8")
    source = tmp_path / "src/bioetl/application/caller.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import bioetl.application._hidden  # EXC-002 private-import waiver\n",
        encoding="utf-8",
    )
    empty = validate_exception_metadata(
        _config(),
        project_root=tmp_path,
        today=_TODAY,
    )
    assert empty == []
    rejected = validate_exception_metadata(
        _config(_pair(id="EXC-002")),
        project_root=tmp_path,
        today=_TODAY,
    )
    assert any("unknown exception id" in error for error in rejected)
    assert not any("caller.py" in error for error in empty)
