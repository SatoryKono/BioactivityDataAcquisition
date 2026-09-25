"""Extracted evaluate_threshold_failures for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (
        JsonDict,
    )


def evaluate_threshold_failures(
    *,
    thresholds: dict[str, int],
    category_scores: dict[str, JsonDict],
) -> list[JsonDict]:
    failures: list[JsonDict] = []
    for category, minimum_score in thresholds.items():
        score_payload = category_scores.get(category)
        actual_score = (
            score_payload.get("score") if isinstance(score_payload, dict) else None
        )
        if not isinstance(actual_score, int):
            failures.append(
                {
                    "category": category,
                    "required": minimum_score,
                    "actual": None,
                    "reason": "category_score_missing",
                }
            )
            continue
        if actual_score >= minimum_score:
            continue
        failures.append(
            {
                "category": category,
                "required": minimum_score,
                "actual": actual_score,
                "reason": "below_required_threshold",
            }
        )
    return failures
