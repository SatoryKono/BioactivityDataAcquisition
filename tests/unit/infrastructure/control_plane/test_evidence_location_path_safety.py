# pyright: reportArgumentType=false
"""Containment checks reject traversal and symlink/junction escape."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationInvalidError,
)
from bioetl.infrastructure.control_plane.evidence_location_path_safety import (
    assert_path_within_trusted_base,
)

pytestmark = pytest.mark.unit


def test_path_within_trusted_base_allows_nested_root(tmp_path: Path) -> None:
    base = (tmp_path / "data").resolve()
    base.mkdir()
    nested = base / "workflow-a" / "chembl_assay"
    nested.mkdir(parents=True)
    assert (
        assert_path_within_trusted_base(nested, trusted_base=base) == nested.resolve()
    )


def test_path_within_trusted_base_allows_missing_leaf(tmp_path: Path) -> None:
    base = (tmp_path / "data").resolve()
    base.mkdir()
    missing = base / "workflow-a" / "chembl_assay"
    resolved = assert_path_within_trusted_base(missing, trusted_base=base)
    assert resolved == missing.resolve(strict=False)


def test_path_rejects_escape_outside_base(tmp_path: Path) -> None:
    base = (tmp_path / "data").resolve()
    base.mkdir()
    outside = (tmp_path / "other").resolve()
    outside.mkdir()
    with pytest.raises(EvidenceLocationInvalidError, match="escapes"):
        assert_path_within_trusted_base(outside, trusted_base=base)


def test_path_rejects_symlink_escape(tmp_path: Path) -> None:
    base = (tmp_path / "data").resolve()
    base.mkdir()
    outside = (tmp_path / "foreign").resolve()
    outside.mkdir()
    link = base / "escape-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    with pytest.raises(EvidenceLocationInvalidError, match="symlink|junction|escapes"):
        assert_path_within_trusted_base(link, trusted_base=base)


@pytest.mark.skipif(os.name == "nt", reason="POSIX absolute path form")
def test_path_rejects_non_absolute_candidate(tmp_path: Path) -> None:
    base = (tmp_path / "data").resolve()
    base.mkdir()
    with pytest.raises(EvidenceLocationInvalidError, match="absolute"):
        assert_path_within_trusted_base(Path("relative/root"), trusted_base=base)
