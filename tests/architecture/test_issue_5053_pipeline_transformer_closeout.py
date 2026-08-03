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
"""Closeout ratchets for issue #5053 pipeline transformer hotspot splits."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

PIPELINE_SEAM_RATCHETS: dict[str, tuple[int, set[str]]] = {
    "src/bioetl/application/pipelines/chembl/activity_transformer.py": (
        250,
        {"bioetl.application.pipelines.chembl._activity_transformer_maps"},
    ),
    "src/bioetl/application/pipelines/pubmed/block_definitions.py": (
        60,
        {
            "bioetl.application.pipelines.pubmed._block_definitions_analytics",
            "bioetl.application.pipelines.pubmed._block_definitions_base",
            "bioetl.application.pipelines.pubmed._block_definitions_edition",
            "bioetl.application.pipelines.pubmed._block_definitions_identifiers",
        },
    ),
    "src/bioetl/application/pipelines/uniprot/extractors/_comment_facets.py": (
        60,
        {
            "bioetl.application.pipelines.uniprot.extractors._comment_facets_all",
            "bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors",
        },
    ),
}


def _path(relative_path: str) -> Path:
    return ROOT / relative_path


def _imported_modules(relative_path: str) -> set[str]:
    tree = ast.parse(_path(relative_path).read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "max_lines", "required_modules"),
    [
        (relative_path, max_lines, required_modules)
        for relative_path, (
            max_lines,
            required_modules,
        ) in PIPELINE_SEAM_RATCHETS.items()
    ],
)
def test_issue_5053_provider_pipeline_modules_stay_thin_and_helper_backed(
    relative_path: str,
    max_lines: int,
    required_modules: set[str],
) -> None:
    """Issue #5053 seams should stay below the reviewed LOC targets."""
    path = _path(relative_path)
    source = path.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count < max_lines, (
        f"{relative_path} regrew to {line_count} lines "
        f"(must stay below {max_lines} for issue #5053 closeout). "
        "Keep provider-local tables, registries, and facet vocabularies in "
        "narrow helper modules instead of re-expanding the public transformer seam."
    )

    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports the extracted provider-owned helpers:\n"
        + "\n".join(sorted(missing_modules))
    )
