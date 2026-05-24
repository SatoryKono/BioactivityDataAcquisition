"""Guardrails for canonical environment-template references."""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
ACTIVE_DOC_ROOTS = (
    ROOT / "README.md",
    ROOT / "docs",
)
ACTIVE_DOC_EXCLUDES = (
    "docs/99-archive/",
    "docs/reports/",
)


def _iter_active_markdown_files(docs_markdown_files: list[Path]) -> list[Path]:
    files: list[Path] = [ROOT / "README.md"]
    files.extend(docs_markdown_files)
    return [
        path
        for path in files
        if not any(
            path.relative_to(ROOT).as_posix().startswith(prefix)
            for prefix in ACTIVE_DOC_EXCLUDES
        )
    ]


@pytest.mark.architecture
def test_root_env_example_exists_as_canonical_template_surface() -> None:
    """The tracked environment template must live at repository root."""
    assert (ROOT / ".env.example").exists()
    assert not (ROOT / "configs" / ".env.example").exists()


@pytest.mark.architecture
def test_active_docs_do_not_reference_noncanonical_configs_env_example(
    docs_markdown_files: list[Path],
    docs_text_cache: dict[Path, str],
) -> None:
    """Contributor-facing docs must not point at configs/.env.example."""
    offending: list[str] = []
    needle = "configs/.env.example"
    for path in _iter_active_markdown_files(docs_markdown_files):
        if path == ROOT / "README.md":
            content = path.read_text(encoding="utf-8")
        else:
            content = docs_text_cache[path]
        if needle in content:
            offending.append(path.relative_to(ROOT).as_posix())

    assert not offending, (
        "Active docs must reference the canonical root .env.example, not "
        f"configs/.env.example: {offending}"
    )


@pytest.mark.architecture
def test_readme_references_root_env_example() -> None:
    """README onboarding should point to the canonical root template."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "[`.env.example`](.env.example)" in readme
    assert "configs/.env.example" not in readme
