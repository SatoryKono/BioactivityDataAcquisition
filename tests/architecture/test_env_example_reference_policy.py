# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Guardrails for canonical environment-template references."""

from __future__ import annotations

import subprocess
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


@pytest.mark.architecture
def test_gitignore_ignores_env_suffix_names_but_keeps_example() -> None:
    """REQ-GOV-011: `.env.*` secret files stay un-addable; template stays tracked."""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env.*" in gitignore
    example_negation_at = gitignore.find("!.env.example")
    env_star_at = gitignore.find(".env.*")
    assert env_star_at != -1
    assert example_negation_at != -1
    assert env_star_at < example_negation_at

    ignored = subprocess.run(
        ["git", "check-ignore", "-v", "--", ".env.production", ".env.development"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0, ignored.stderr
    assert ".env.*" in ignored.stdout

    template = subprocess.run(
        ["git", "check-ignore", "--", ".env.example"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert template.returncode == 1, template.stdout


@pytest.mark.architecture
def test_dockerignore_excludes_env_suffix_names() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert ".env.*" in dockerignore.splitlines()
