"""Unit coverage for documentation cleanup inventory link handling."""

from __future__ import annotations

import pytest

from scripts.docs.checks import documentation_cleanup_inventory as inventory

pytestmark = pytest.mark.unit


def test_outgoing_links_keeps_windows_absolute_paths() -> None:
    """Windows drive paths should be treated as local links, not URI schemes."""
    text = r"[evidence](E:\repo\reports\semantic_pipeline_audit\audit.md:12)"

    assert inventory._outgoing_links(text) == [
        r"E:\repo\reports\semantic_pipeline_audit\audit.md:12"
    ]


def test_resolve_link_maps_wsl_absolute_repo_alias_on_windows(
    monkeypatch,
) -> None:
    """WSL-style absolute links should resolve when PROJECT_ROOT is Windows-style."""
    class FakeRoot:
        def resolve(self) -> FakeRoot:
            return self

        def as_posix(self) -> str:
            return "E:/g-drive/05_AI/github/BioactivityDataAcquisition2"

    monkeypatch.setattr(inventory, "PROJECT_ROOT", FakeRoot())

    resolved = inventory._resolve_link(
        "reports/semantic_pipeline_audit/source.md",
        (
            "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/"
            "reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-15.csv:25"
        ),
    )

    assert (
        resolved
        == "reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-15.csv"
    )


def test_resolve_link_normalizes_relative_paths_without_filesystem() -> None:
    """Relative markdown targets should resolve lexically for deterministic inventory."""
    resolved = inventory._resolve_link(
        "docs/03-guides/source.md",
        "../02-architecture/decisions/ADR-001-example.md:12",
    )

    assert resolved == "docs/02-architecture/decisions/ADR-001-example.md"
