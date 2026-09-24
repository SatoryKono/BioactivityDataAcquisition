"""Extracted score_lineage_completeness for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core import (
    JsonDict as JsonDict,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core import (
    ScoreCardRecord as ScoreCardRecord,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core import (
    build_score_card_record as build_score_card_record,
)


def score_lineage_completeness(summary: JsonDict) -> ScoreCardRecord:
    evidence = []
    blockers = []
    refs = [
        "diagnostics.identity_graph_complete",
        "diagnostics.lineage_fragment_ids",
        "diagnostics.lineage_closure_boundary",
    ]
    score = 10
    if not summary.get("identity_graph_complete"):
        score -= 2
        evidence.append("identity_graph_incomplete")
        blockers.append("identity_graph_incomplete")
    lineage_boundary = summary.get("lineage_closure_boundary")
    if isinstance(lineage_boundary, dict) and not bool(
        lineage_boundary.get("supported")
    ):
        score -= 2
        evidence.append("lineage_closure_boundary_unsupported")
        blockers.append("lineage_closure_boundary_unsupported")
    if summary.get("missing_artifact_links", 0):
        score -= 2
        evidence.append("artifact_lineage_links_missing")
        blockers.append("artifact_lineage_links_missing")
    if not summary.get("lineage_fragment_ids"):
        score -= 1
        evidence.append("no_lineage_fragments_observed")
    return build_score_card_record(
        "lineage_completeness", score, evidence, blockers, refs
    )
