"""Fixed owned worker for explicit closeout commands; no native event adapter."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from memory import proof
from scripts.engineering.repo import closeout_state as state
from scripts.engineering.repo import hook_receipts


def _verify(request: dict[str, Any], root: Path) -> dict[str, Any]:
    """Use the canonical core and preserve its verdict below a local trust cap."""
    stream = sys.stdin.buffer
    raw = state.bundle_bytes(stream)
    if state.sha256(raw) != request["bundle_sha256"]:
        return state.result("ERROR", "bundle_changed", request["event_id"])
    before = state.capture(root, os.environ)
    if before != request["state"]:
        return state.result(
            "ERROR", "source_or_environment_changed", request["event_id"]
        )
    bundle = json.loads(raw)
    if not isinstance(bundle, dict):
        raise ValueError("invalid bundle shape")
    if not state.scope_matches(
        bundle,
        root,
        task_hash=request["task_id_sha256"],
        runtime=request["runtime"],
        claim=request["claim"],
    ):
        return state.result(
            "STOP", "task_runtime_claim_or_branch_mismatch", request["event_id"]
        )
    verified = proof.verify_bundle(
        bundle=bundle,
        repo_root=root,
        policy=proof.load_policy(),
        schema=proof.load_schema(),
        check_current_source=True,
    )
    if (
        state.capture(root, os.environ) != before
        or state.sha256(state.bundle_bytes(stream)) != request["bundle_sha256"]
        or not state.bundle_path_matches(root, Path(request["bundle_path"]), stream)
    ):
        return state.result("ERROR", "source_or_bundle_changed", request["event_id"])
    return _verdict(verified, request, before)


def _verdict(
    verified: proof.VerificationResult, request: dict[str, Any], before: dict[str, Any]
) -> dict[str, Any]:
    # Strings in evidence findings may be caller-controlled. Only counts/hashes
    # leave the worker, never exception text, source contents or raw findings.
    if verified.outcome not in {"ADMIT", "STOP", "DEGRADED"}:
        raise ValueError("unqualified core outcome")
    outcome = "STOP" if verified.outcome == "STOP" else "DEGRADED"
    reason = "core_rejected" if outcome == "STOP" else "local_transport_not_attested"
    return {
        **state.result(outcome, reason, request["event_id"]),
        "core_outcome": verified.outcome,
        "errors_count": len(verified.errors),
        "degradations_count": len(verified.degradations),
        "findings_sha256": hook_receipts.digest(
            [verified.errors, verified.degradations]
        ),
        "state_sha256": hook_receipts.digest(before),
        "bundle_sha256": request["bundle_sha256"],
    }


def run(root: Path, event: str) -> int:
    """An operational zero means a result exists, never an admitted claim."""
    if os.environ.get("BIOETL_CLOSEOUT_WORKER") != "1":
        return 2
    target = state.directory(root, event)
    request = state.read(target, "request.json")
    if (
        request.get("kind") != state.REQUEST_KIND
        or request.get("root") != str(root)
        or request.get("event_id") != event
        or request.get("runtime") not in state.RUNTIMES
        or request.get("claim") not in state.CLAIMS
    ):
        return 2
    state.write_once(
        target, "worker.lock", {"request_sha256": request["payload_sha256"]}
    )
    try:
        payload = _verify(request, root)
    except Exception:
        # The protocol boundary must not expose arbitrary bundle/Git diagnostics.
        payload = state.result("ERROR", "verification_unavailable", event)
    state.write_once(
        target, "result.json", {**payload, "request_sha256": request["payload_sha256"]}
    )
    return 0
