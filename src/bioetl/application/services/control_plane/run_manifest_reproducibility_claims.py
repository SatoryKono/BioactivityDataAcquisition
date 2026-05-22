"""Project-wide reproducibility claim payload builders."""

from __future__ import annotations

JsonDict = dict[str, object]


def build_global_reproducibility_claim(
    *,
    summary: JsonDict,
    evidence_refs: list[str],
) -> JsonDict:
    historical_universe_claim = summary.get("historical_replay_universe_claim")
    historical_universe_source = summary.get("historical_replay_universe_claim_source")
    if isinstance(historical_universe_claim, dict):
        claim_refs = sorted(
            dict.fromkeys(
                [
                    *evidence_refs,
                    "diagnostics.historical_replay_universe_claim",
                    "diagnostics.exact_replay_support_boundary",
                    "diagnostics.lineage_closure_boundary",
                    "diagnostics.replay_family_contract",
                ]
            )
        )
        artifact_path = (
            str(historical_universe_source).strip()
            if isinstance(historical_universe_source, str)
            else None
        )
        exact_replay_supported = bool(historical_universe_claim.get("claimed"))
        durable_supported = bool(
            summary.get("historical_replay_universe_durable_evidence_claimed", False)
        )
        fully_claimed = exact_replay_supported and durable_supported
        return {
            "scope": "project_wide_exact_replay",
            "claimed": fully_claimed,
            "verdict": (
                "universal_exact_replay_claimed"
                if fully_claimed
                else "universal_exact_replay_not_claimed"
            ),
            "reason": (
                "latest_historical_replay_universe_artifact_supports_universal_claim"
                if fully_claimed
                else (
                    "historical_replay_universe_artifact_blocks_universal_claim"
                    if not exact_replay_supported
                    else "durable_evidence_coverage_blocks_universal_claim"
                )
            ),
            "exact_replay_support_boundary": summary.get(
                "exact_replay_support_boundary"
            ),
            "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
            "authoritative_truth_surface": "historical_replay_universe_closure_report",
            "claim_source_artifact_path": artifact_path,
            "evidence_refs": claim_refs,
        }
    claim_refs = sorted(
        dict.fromkeys(
            [
                *evidence_refs,
                "diagnostics.exact_replay_support_boundary",
                "diagnostics.lineage_closure_boundary",
                "diagnostics.replay_family_contract",
            ]
        )
    )
    return {
        "scope": "project_wide_exact_replay",
        "claimed": False,
        "verdict": "universal_exact_replay_not_claimed",
        "reason": "published_contract_limits_exact_replay_to_supported_boundary",
        "exact_replay_support_boundary": summary.get("exact_replay_support_boundary"),
        "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
        "authoritative_truth_surface": "historical_replay_universe_closure_report",
        "claim_source_artifact_path": None,
        "evidence_refs": claim_refs,
    }


__all__ = ["build_global_reproducibility_claim"]
