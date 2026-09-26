"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re

from memory.graph.sync_pkg._core_convert import GITHUB_PATH_PREFIX, YAML_SUFFIX
from memory.graph.sync_pkg.graph_snapshot import GraphNode

__all__ = [
    "_DOCS_DRIFT_TEXT_EXTENSIONS",
    "_DOCS_REFERENCE_ALLOWED_PREFIXES",
    "_DOC_LIKE_LABELS",
    "_heading_anchor_slug",
    "_is_docs_drift_source_candidate",
    "_trim_docs_reference_candidate",
]

_DOCS_REFERENCE_ALLOWED_PREFIXES = (
    "src/",
    "configs/",
    "scripts/",
    "tests/",
    "docs/",
    "grafana/",
    GITHUB_PATH_PREFIX,
)

_DOC_LIKE_LABELS = {"doc_source_surface", "doc_artifact", "policy_surface"}
_DOCS_DRIFT_TEXT_EXTENSIONS = {".md", ".rst", ".txt", YAML_SUFFIX, ".yml"}


def _is_docs_drift_source_candidate(node: GraphNode) -> bool:
    """Return whether a doc-like node should be parsed for docs-code drift.

    File-structure ingestion creates one ``doc_artifact`` per tracked document.
    Parsing all of them turns snapshot invariants into a root-wide filesystem
    scan on mounted Windows/WSL checkouts. Curated docs and policy surfaces are
    the supported drift sources; file-structure artifacts remain represented in
    the graph through ``HAS_DOC_ARTIFACT``/``BACKED_BY`` edges.
    """
    if node.key.label != "doc_artifact":
        return True
    return "repo_zone" not in node.properties


def _trim_docs_reference_candidate(raw_ref: str) -> str:
    return raw_ref.strip().strip("`").rstrip(".,:;)]}")


def _heading_anchor_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "section"
