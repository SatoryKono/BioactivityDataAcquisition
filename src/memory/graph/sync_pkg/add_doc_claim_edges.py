"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re
from datetime import date

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_claim_target_relation import _add_claim_fallback_target
from memory.graph.sync_pkg.add_claim_token_targets import _add_claim_token_targets
from memory.graph.sync_pkg.claim_line_context import (
    _add_claim_path_targets,
    _claim_line_context,
    _claim_section_context,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.workflow_output_expression import _claim_modality

__all__ = [
    "_add_doc_claim_edges",
]


def _add_doc_claim_edges(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    source_path: str,
    text: str,
    path_pattern: re.Pattern[str],
) -> None:
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        claim_line = _claim_line_context(raw_line)
        if claim_line is None:
            continue
        section_title, section_anchor = _claim_section_context(text, raw_line)
        claim = snapshot.add_node(
            "doc_claim_surface",
            f"{source_path}#L{line_number}",
            summary=f"Claim extracted from `{source_path}`.",
            source_path=source_path,
            source_kind="doc_claim_surface",
            claim_text=claim_line.clean_text,
            modality=_claim_modality(claim_line.clean_text),
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            last_verified=str(date.today()),
            ingest_wave="repo_sync_v1",
            confidence="medium",
        )
        snapshot.add_relation(source_node, "ASSERTS", claim, provenance="docs_claims")
        claim_has_target = _add_claim_path_targets(
            snapshot,
            claim,
            source_node,
            claim_line.stripped,
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            path_pattern=path_pattern,
        )
        claim_has_target = (
            _add_claim_token_targets(
                snapshot,
                claim,
                claim_line.clean_text,
                section_title=section_title,
                section_anchor=section_anchor,
                line_number=line_number,
            )
            or claim_has_target
        )
        if not claim_has_target:
            _add_claim_fallback_target(
                snapshot,
                claim,
                source_path,
                section_title=section_title,
                section_anchor=section_anchor,
                line_number=line_number,
            )
