"""Explicit local closeout facade; native hooks remain disabled/unqualified."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, BinaryIO, Never

from scripts.engineering.repo import closeout_state as state
from scripts.engineering.repo import hook_receipts
from scripts.engineering.repo.process_deadline import run_owned

_RESULT_FIELDS = {
    "kind",
    "outcome",
    "exit_code",
    "reason",
    "event_id",
    "claim_qualified",
    "runtime_admission",
    "ci_acceptance",
    "native_event_observed",
    "core_outcome",
    "errors_count",
    "degradations_count",
    "findings_sha256",
    "state_sha256",
    "bundle_sha256",
    "request_sha256",
    "payload_sha256",
}
_WORKER_REASONS = {
    "bundle_changed",
    "source_or_environment_changed",
    "task_runtime_claim_or_branch_mismatch",
    "source_or_bundle_changed",
    "core_rejected",
    "local_transport_not_attested",
    "verification_unavailable",
}
_VERIFIED_FIELDS = {
    "core_outcome",
    "errors_count",
    "degradations_count",
    "findings_sha256",
    "state_sha256",
    "bundle_sha256",
}


def _environment() -> dict[str, str]:
    """A supplied index is intentional; inherited Git execution controls are not."""
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") or key == "GIT_INDEX_FILE"
    }
    env.update(PYTHONDONTWRITEBYTECODE="1", BIOETL_CLOSEOUT_WORKER="1")
    return env


def _worker_argv(root: Path, event: str) -> tuple[str, ...]:
    entry = (
        "import sys;from pathlib import Path;source=sys.argv.pop(1);"
        "sys.path[:0]=[source,str(Path(source)/'src')];"
        "from scripts.engineering.repo.closeout_worker import run;"
        "raise SystemExit(run(Path(sys.argv[1]),sys.argv[2]))"
    )
    return (
        sys.executable,
        "-I",
        "-B",
        "-c",
        entry,
        str(state.SOURCE_ROOT),
        str(root),
        event,
    )


def _validate_header(payload: dict[str, Any], request: dict[str, Any]) -> None:
    if (
        payload.get("kind") != state.RESULT_KIND
        or payload.get("event_id") != request["event_id"]
        or payload.get("request_sha256") != request["payload_sha256"]
        or payload.get("outcome") not in {"STOP", "DEGRADED", "ERROR"}
        or payload.get("exit_code") != (3 if payload["outcome"] == "DEGRADED" else 2)
        or any(
            payload.get(key) is not False
            for key in (
                "claim_qualified",
                "runtime_admission",
                "ci_acceptance",
                "native_event_observed",
            )
        )
    ):
        raise ValueError("unqualified worker result")
    if set(payload) - _RESULT_FIELDS or payload.get("reason") not in _WORKER_REASONS:
        raise ValueError("unqualified worker fields")
    if payload["reason"] in {"core_rejected", "local_transport_not_attested"}:
        if not _VERIFIED_FIELDS <= set(payload):
            raise ValueError("missing verification fields")
        rejected = payload["reason"] == "core_rejected"
        if (
            payload["outcome"] != ("STOP" if rejected else "DEGRADED")
            or (payload["core_outcome"] == "STOP") is not rejected
        ):
            raise ValueError("inconsistent core qualification")
    elif payload["outcome"] != (
        "STOP"
        if payload["reason"] == "task_runtime_claim_or_branch_mismatch"
        else "ERROR"
    ):
        raise ValueError("inconsistent failure qualification")


def _validate_details(payload: dict[str, Any], request: dict[str, Any]) -> None:
    if "core_outcome" in payload and payload["core_outcome"] not in {
        "ADMIT",
        "STOP",
        "DEGRADED",
    }:
        raise ValueError("unqualified core outcome")
    for field in ("errors_count", "degradations_count"):
        if field in payload and (
            type(payload[field]) is not int or not 0 <= payload[field] <= state.LIMIT
        ):
            raise ValueError("unqualified finding count")
    for field in ("findings_sha256", "state_sha256", "bundle_sha256"):
        if field in payload and (
            not isinstance(payload[field], str)
            or re.fullmatch(r"[a-f0-9]{64}", payload[field]) is None
        ):
            raise ValueError("unqualified result digest")
    if "state_sha256" in payload and payload["state_sha256"] != hook_receipts.digest(
        request["state"]
    ):
        raise ValueError("worker state mismatch")
    if (
        "bundle_sha256" in payload
        and payload["bundle_sha256"] != request["bundle_sha256"]
    ):
        raise ValueError("worker bundle mismatch")


def _consume(target: Path, request: dict[str, Any]) -> dict[str, Any]:
    payload = state.read(target, "result.json")
    _validate_header(payload, request)
    _validate_details(payload, request)
    return payload


def _invoke(
    root: Path,
    stream: BinaryIO,
    target: Path,
    request: dict[str, Any],
    env: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    event = request["event_id"]
    execution = run_owned(
        _worker_argv(root, event),
        cwd=root,
        state_dir=target,
        timeout=timeout,
        input_stream=stream,
        env=env,
    )
    if execution.status != "PASS":
        reason = {
            "timeout": "worker_timeout",
            "containment_cleanup_failed": "worker_cleanup_failed",
            "supervisor_failure": "worker_cleanup_failed",
        }.get(execution.reason, "worker_failed")
        return state.result("ERROR", reason, event)
    if (
        state.capture(root, env) != request["state"]
        or state.sha256(state.bundle_bytes(stream)) != request["bundle_sha256"]
    ):
        return state.result("ERROR", "source_or_bundle_changed", event)
    return _consume(target, request)


def _perform(
    root: Path, bundle: Path, identity: dict[str, str], event: str, timeout: float
) -> dict[str, Any]:
    env = _environment()
    with state.bundle_stream(root, bundle) as stream:
        raw = state.bundle_bytes(stream)
        if not state.scope_matches(
            json.loads(raw),
            root,
            task_hash=identity["task_id_sha256"],
            runtime=identity["runtime"],
            claim=identity["claim"],
        ):
            return state.result("STOP", "task_runtime_claim_or_branch_mismatch", event)
        target = state.directory(root, event, reserve=True)
        request = state.write_once(
            target,
            "request.json",
            {
                **identity,
                "kind": state.REQUEST_KIND,
                "event_id": event,
                "root": str(root),
                "bundle_sha256": state.sha256(raw),
                "state": state.capture(root, env),
            },
        )
        return _invoke(root, stream, target, request, env, timeout)


def verify(
    root: Path,
    bundle: Path,
    *,
    task_id: str,
    runtime: str,
    claim: str,
    event_id: str | None = None,
    timeout: float = 120,
) -> dict[str, Any]:
    """A bounded explicit observation; no CI transport, ingest, agents or services."""
    event: str | None = None
    try:
        if (
            os.environ.get("BIOETL_CLOSEOUT_WORKER")
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", task_id) is None
            or runtime not in state.RUNTIMES
            or claim not in state.CLAIMS
            or isinstance(timeout, bool)
            or not math.isfinite(timeout)
            or not 0 < timeout <= 120
        ):
            return state.result("ERROR", "invalid_or_recursive_request", None)
        event = state.event_identity(event_id)
        root = root.resolve(strict=True)
        identity = {
            "task_id_sha256": state.sha256(task_id.encode()),
            "runtime": runtime,
            "claim": claim,
        }
        return _perform(root, bundle, identity, event, timeout)
    except KeyboardInterrupt:
        # run_owned propagates the actual parent interruption after cleanup.
        return state.result("USER_STOP", "parent_interrupted", event)
    except FileExistsError:
        return state.result("ERROR", "duplicate_or_reentered_event", event)
    except Exception:
        return state.result("ERROR", "request_or_state_unavailable", event)


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> Never:
        self.exit(2, "closeout ERROR: invalid arguments\n")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        description=__doc__, prog="python -m scripts.engineering.repo closeout"
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--runtime", choices=sorted(state.RUNTIMES), required=True)
    parser.add_argument("--claim", choices=sorted(state.CLAIMS), required=True)
    parser.add_argument("--event-id")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args(argv)
    payload = verify(
        args.repo_root,
        args.bundle,
        task_id=args.task_id,
        runtime=args.runtime,
        claim=args.claim,
        event_id=args.event_id,
        timeout=args.timeout,
    )
    print(json.dumps(payload, sort_keys=True))
    return int(payload["exit_code"])
