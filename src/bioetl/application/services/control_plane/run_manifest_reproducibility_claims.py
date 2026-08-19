from __future__ import annotations

from bioetl.application.services._historical_claim_reason import (
    historical_universe_claim_reason,
)

JsonDict = dict[str, object]


def _claim_evidence_refs(
    *,
    evidence_refs: list[str],
    include_historical_claim: bool,
) -> list[str]:
    refs = [
        *evidence_refs,
        "diagnostics.exact_replay_support_boundary",
        "diagnostics.lineage_closure_boundary",
        "diagnostics.replay_family_contract",
    ]
    if include_historical_claim:
        refs.append("diagnostics.historical_replay_universe_claim")
    return sorted(dict.fromkeys(refs))


def build_historical_replay_universe_exact_replay_claim(
    *,
    summary: JsonDict,
    evidence_refs: list[str],
) -> JsonDict:
    historical_universe_claim = summary.get("historical_replay_universe_claim")
    historical_universe_source = summary.get("historical_replay_universe_claim_source")
    governed_gate = summary.get("historical_replay_universe_governed_full_corpus_gate")
    if not isinstance(governed_gate, dict):
        governed_gate = {
            "gate_kind": "universal_historical_exact_replay",
            "scope": "all_known_historical_runs",
            "authoritative_truth_surface": "historical_replay_universe_closure_report",
            "required_claims": {
                "universal_claim": False,
                "durable_evidence_coverage_claim": False,
            },
            "satisfied": False,
            "verdict": "gate_blocked",
            "reason": "authoritative_historical_replay_universe_artifact_unavailable",
        }
    if isinstance(historical_universe_claim, dict):
        claim_refs = _claim_evidence_refs(
            evidence_refs=evidence_refs,
            include_historical_claim=True,
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
        governed_gate_satisfied = bool(governed_gate.get("satisfied"))
        fully_claimed = (
            exact_replay_supported and durable_supported and governed_gate_satisfied
        )
        claim_reason = historical_universe_claim_reason(
            fully_claimed=fully_claimed,
            exact_replay_supported=exact_replay_supported,
            durable_supported=durable_supported,
        )
        return {
            "scope": str(
                historical_universe_claim.get("scope") or "all_known_historical_runs"
            ),
            "claimed": fully_claimed,
            "verdict": (
                "historical_universe_exact_replay_claimed"
                if fully_claimed
                else "historical_universe_exact_replay_not_claimed"
            ),
            "reason": claim_reason,
            "exact_replay_support_boundary": summary.get(
                "exact_replay_support_boundary"
            ),
            "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
            "authoritative_truth_surface": "historical_replay_universe_closure_report",
            "claim_source_artifact_path": artifact_path,
            "governed_full_corpus_gate": governed_gate,
            "evidence_refs": claim_refs,
        }
    claim_refs = _claim_evidence_refs(
        evidence_refs=evidence_refs,
        include_historical_claim=False,
    )
    return {
        "scope": "all_known_historical_runs",
        "claimed": False,
        "verdict": "historical_universe_exact_replay_not_claimed",
        "reason": "authoritative_historical_replay_universe_artifact_unavailable",
        "exact_replay_support_boundary": summary.get("exact_replay_support_boundary"),
        "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
        "authoritative_truth_surface": "historical_replay_universe_closure_report",
        "claim_source_artifact_path": None,
        "governed_full_corpus_gate": governed_gate,
        "evidence_refs": claim_refs,
    }


def build_executable_run_contract_claim(
    *,
    summary: JsonDict,
    evidence_refs: list[str],
) -> JsonDict:
    claim_refs = _claim_evidence_refs(
        evidence_refs=evidence_refs,
        include_historical_claim=False,
    )
    return {
        "scope": "prospective_executable_runs_within_supported_boundary",
        "claimed": True,
        "verdict": "prospective_executable_run_contract_claimed",
        "reason": "supported_boundary_executable_runs_promote_or_fail_closed",
        "exact_replay_support_boundary": summary.get("exact_replay_support_boundary"),
        "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
        "authoritative_truth_surface": "published_control_plane_contract",
        "claim_source_artifact_path": (
            "docs/04-reference/contracts/run-manifest-ledger.md"
        ),
        "evidence_refs": claim_refs,
    }


__all__ = [
    "build_executable_run_contract_claim",
    "build_historical_replay_universe_exact_replay_claim",
]
