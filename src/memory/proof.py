"""Offline source-bound evidence primitives for the Proof-or-Stop gate."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = ROOT / "configs" / "quality" / "proof_or_stop_policy.yaml"
DEFAULT_SCHEMA_PATH = ROOT / "configs" / "quality" / "proof_or_stop_bundle.schema.json"
PROOF_REPORT_PREFIX = "reports/quality/proof-or-stop/"
OUTCOME_EXIT_CODES = {"ADMIT": 0, "STOP": 2, "DEGRADED": 3}
DEFAULT_GIT_TIMEOUT_SECONDS = 20.0
MAX_GIT_DIFF_TIMEOUT_SECONDS = 300.0


class ProofError(ValueError):
    """Raised when evidence cannot be assembled or validated safely."""


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Stable verifier result returned to CLI, CI, and tests."""

    outcome: str
    claim_qualified: bool
    errors: tuple[str, ...]
    degradations: tuple[str, ...]

    @property
    def exit_code(self) -> int:
        """Return the stable process exit code for this outcome."""
        return OUTCOME_EXIT_CODES[self.outcome]

    def to_dict(self) -> dict[str, Any]:
        """Render a stable machine-readable result."""
        return {
            "schema_version": 1,
            "outcome": self.outcome,
            "claim_qualified": self.claim_qualified,
            "errors": list(self.errors),
            "degradations": list(self.degradations),
            "exit_code": self.exit_code,
        }


@dataclass(frozen=True, slots=True)
class ReceiptInput:
    """Producer execution fields normalized into one evidence receipt."""

    receipt_id: str
    producer: str
    evidence_kind: str
    command: str
    argv: list[str]
    cwd: str
    started_at: str
    duration_ms: int
    exit_code: int | None
    status: str
    output_path: Path | None
    skip_reason: str | None = None
    follow_up: str | None = None


def canonical_digest(payload: Any) -> str:
    """Hash one JSON-compatible payload using the canonical encoding."""
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path: Path | None) -> str:
    """Hash an output artifact, using the empty digest when no file exists."""
    if path is None or not path.exists() or not path.is_file():
        return hashlib.sha256(b"").hexdigest()
    path = path.expanduser().resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    """Load the canonical gate policy as a mapping."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ProofError(f"policy must be a mapping: {path}")
    return payload


def load_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    """Load the canonical evidence bundle JSON schema."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProofError(f"schema must be an object: {path}")
    Draft202012Validator.check_schema(payload)
    return payload


def _git(
    repo_root: Path,
    *args: str,
    timeout: float = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ProofError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def _git_text(
    repo_root: Path,
    *args: str,
    timeout: float = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> str:
    return (
        _git(repo_root, *args, timeout=timeout)
        .decode("utf-8", errors="replace")
        .strip()
    )


def _git_diff_timeout(policy: dict[str, Any]) -> float:
    source_binding = policy.get("source_binding", {})
    if not isinstance(source_binding, dict):
        raise ProofError("policy source_binding must be a mapping")
    configured = source_binding.get(
        "git_diff_timeout_seconds", DEFAULT_GIT_TIMEOUT_SECONDS
    )
    if isinstance(configured, bool) or not isinstance(configured, (int, float)):
        raise ProofError("source_binding.git_diff_timeout_seconds must be a number")
    timeout = float(configured)
    if not 1.0 <= timeout <= MAX_GIT_DIFF_TIMEOUT_SECONDS:
        raise ProofError(
            "source_binding.git_diff_timeout_seconds must be between "
            f"1 and {MAX_GIT_DIFF_TIMEOUT_SECONDS:g}"
        )
    return timeout


def _excluded(path: str, policy: dict[str, Any]) -> bool:
    configured = policy.get("source_binding", {}).get("excluded_prefixes", [])
    prefixes = [PROOF_REPORT_PREFIX, *[str(item) for item in configured]]
    normalized = path.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in prefixes)


def _repository_paths(repo_root: Path, policy: dict[str, Any]) -> list[str]:
    raw = _git(repo_root, "ls-files", "-co", "--exclude-standard", "-z")
    paths = {
        item.decode("utf-8", errors="surrogateescape")
        for item in raw.split(b"\0")
        if item
    }
    return sorted(path for path in paths if not _excluded(path, policy))


def _untracked_paths(repo_root: Path, policy: dict[str, Any]) -> list[str]:
    raw = _git(repo_root, "ls-files", "--others", "--exclude-standard", "-z")
    paths = [
        item.decode("utf-8", errors="surrogateescape")
        for item in raw.split(b"\0")
        if item
    ]
    return sorted(path for path in paths if not _excluded(path, policy))


def _hash_paths(repo_root: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for relative in paths:
        path = repo_root / relative
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(
                str(path.readlink()).encode("utf-8", errors="surrogateescape")
            )
        elif path.is_file():
            digest.update(b"file\0")
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            digest.update(b"missing\0")
        digest.update(b"\0")
    return digest.hexdigest()


def _task_diff_state(
    repo_root: Path,
    policy: dict[str, Any],
    untracked_paths: list[str],
    *,
    timeout: float,
) -> tuple[str, bool]:
    tracked_diff = _git(
        repo_root,
        "diff",
        "--binary",
        "--no-ext-diff",
        "HEAD",
        "--",
        timeout=timeout,
    )
    digest = hashlib.sha256()
    digest.update(tracked_diff)
    digest.update(b"\0untracked\0")
    digest.update(_hash_paths(repo_root, untracked_paths).encode("ascii"))
    digest.update(canonical_digest(policy).encode("ascii"))
    return digest.hexdigest(), bool(tracked_diff)


def _repo_id(repo_root: Path) -> str:
    try:
        remote = _git_text(repo_root, "remote", "get-url", "origin")
    except ProofError:
        remote = repo_root.name
    normalized = remote.removesuffix(".git").rstrip("/")
    return normalized.rsplit("/", 1)[-1].lower()


def command_set_hash(policy: dict[str, Any], claim: str) -> str:
    """Hash only the command/evidence policy applicable to one claim."""
    claims = policy.get("claims", {})
    claim_policy = claims.get(claim)
    if not isinstance(claim_policy, dict):
        raise ProofError(f"unsupported claim: {claim}")
    evidence_kinds = policy.get("evidence_kinds", {})
    required = claim_policy.get("required_evidence", [])
    command_set = {
        "claim": claim,
        "required_evidence": required,
        "evidence_kinds": {kind: evidence_kinds.get(kind) for kind in sorted(required)},
    }
    return canonical_digest(command_set)


def discover_context(
    repo_root: Path,
    *,
    policy: dict[str, Any],
    claim: str,
    ci_run_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Discover repository and source identity without network access."""
    root = Path(_git_text(repo_root, "rev-parse", "--show-toplevel")).resolve()
    git_diff_timeout = _git_diff_timeout(policy)
    untracked = _untracked_paths(root, policy)
    paths = _repository_paths(root, policy)
    worktree_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    repository = {
        "repo_id": _repo_id(root),
        "branch": _git_text(root, "branch", "--show-current") or "detached",
        "worktree_id": worktree_id,
        "ci_run_id": ci_run_id,
    }
    task_diff_hash, tracked_dirty = _task_diff_state(
        root, policy, untracked, timeout=git_diff_timeout
    )
    source = {
        "head_sha": _git_text(root, "rev-parse", "HEAD"),
        "material_hash": _hash_paths(root, paths),
        "task_diff_hash": task_diff_hash,
        "policy_hash": canonical_digest(policy),
        "command_set_hash": command_set_hash(policy, claim),
        "dirty": tracked_dirty or bool(untracked),
        "untracked_paths": untracked,
    }
    return repository, source


def build_plan(
    *,
    repo_root: Path,
    policy: dict[str, Any],
    run_id: str,
    task_id: str,
    claim: str,
    ci_run_id: str | None = None,
) -> dict[str, Any]:
    """Build a source-bound plan for the requested claim."""
    repository, source = discover_context(
        repo_root, policy=policy, claim=claim, ci_run_id=ci_run_id
    )
    claim_policy = policy["claims"][claim]
    required = list(claim_policy["required_evidence"])
    plan = {
        "schema_version": 1,
        "run_id": run_id,
        "task_id": task_id,
        "claim": claim,
        "repository": repository,
        "source": source,
        "acceptance": {
            "required_evidence": required,
            "require_full_trust": bool(claim_policy.get("require_full_trust")),
        },
        "required_receipts": [
            {
                "evidence_kind": kind,
                **policy["evidence_kinds"][kind],
            }
            for kind in required
        ],
    }
    plan["plan_digest"] = canonical_digest(plan)
    return plan


def build_receipt(
    *,
    repo_root: Path,
    policy: dict[str, Any],
    task_id: str,
    claim: str,
    receipt_input: ReceiptInput,
    trust_tier: str,
    ci_run_id: str | None = None,
) -> dict[str, Any]:
    """Normalize one producer result into a source-bound receipt."""
    if receipt_input.status not in {"pass", "fail", "skip", "unavailable"}:
        raise ProofError(f"unsupported receipt status: {receipt_input.status}")
    repository, source = discover_context(
        repo_root, policy=policy, claim=claim, ci_run_id=ci_run_id
    )
    tiers = policy.get("trust_tiers", {})
    tier = tiers.get(trust_tier)
    if not isinstance(tier, dict):
        raise ProofError(f"unsupported trust tier: {trust_tier}")
    receipt = {
        "receipt_id": receipt_input.receipt_id,
        "producer": receipt_input.producer,
        "evidence_kind": receipt_input.evidence_kind,
        "command": receipt_input.command,
        "argv": receipt_input.argv,
        "cwd": receipt_input.cwd,
        "started_at": receipt_input.started_at,
        "duration_ms": receipt_input.duration_ms,
        "exit_code": receipt_input.exit_code,
        "status": receipt_input.status,
        "skip_reason": receipt_input.skip_reason,
        "follow_up": receipt_input.follow_up,
        "output_digest": file_digest(receipt_input.output_path),
        "source": source,
        "repository": repository,
        "task_id": task_id,
        "execution_attestation": tier["execution_attestation"],
    }
    receipt["receipt_digest"] = canonical_digest(receipt)
    return receipt


def emit_receipt_from_environment(
    *,
    repo_root: Path,
    producer: str,
    evidence_kind: str,
    command: str,
    status: str,
    exit_code: int | None,
    output_path: Path | None,
    duration_ms: int = 0,
    skip_reason: str | None = None,
    follow_up: str | None = None,
) -> Path | None:
    """Emit a normalized receipt when the closeout environment is enabled.

    Existing producers call this after writing their canonical report. With no
    ``PROOF_OR_STOP_RUN_ID`` the function is a no-op, preserving fast local and
    pre-commit behavior.
    """
    run_id = os.environ.get("PROOF_OR_STOP_RUN_ID")
    if not run_id:
        return None
    task_id = os.environ.get("PROOF_OR_STOP_TASK_ID")
    claim = os.environ.get("PROOF_OR_STOP_CLAIM", "ready_to_merge")
    if not task_id:
        raise ProofError(
            "PROOF_OR_STOP_TASK_ID is required when receipt capture is enabled"
        )
    trust_tier = os.environ.get("PROOF_OR_STOP_TRUST_TIER", "local_single_host")
    ci_run_id = os.environ.get("PROOF_OR_STOP_CI_RUN_ID") or os.environ.get(
        "GITHUB_RUN_ID"
    )
    job = os.environ.get("GITHUB_JOB") or os.environ.get("CI_JOB_NAME") or "local"
    receipt_id = f"{producer}-{job}"
    policy_path = repo_root / "configs/quality/proof_or_stop_policy.yaml"
    if not policy_path.exists():
        policy_path = DEFAULT_POLICY_PATH
    policy = load_policy(policy_path)
    receipt = build_receipt(
        repo_root=repo_root,
        policy=policy,
        task_id=task_id,
        claim=claim,
        receipt_input=ReceiptInput(
            receipt_id=receipt_id,
            producer=producer,
            evidence_kind=evidence_kind,
            command=command,
            argv=[],
            cwd=str(repo_root.resolve()),
            started_at=datetime_now_utc(),
            duration_ms=duration_ms,
            exit_code=exit_code,
            status=status,
            output_path=output_path,
            skip_reason=skip_reason,
            follow_up=follow_up,
        ),
        trust_tier=trust_tier,
        ci_run_id=ci_run_id,
    )
    receipt_dir = Path(
        os.environ.get(
            "PROOF_OR_STOP_RECEIPT_DIR",
            str(repo_root / "reports/quality/proof-or-stop" / run_id / "receipts"),
        )
    )
    path = receipt_dir / f"{receipt_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def datetime_now_utc() -> str:
    """Return an RFC 3339 timestamp without importing runtime-specific clocks."""
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def assemble_bundle(
    *,
    repo_root: Path,
    policy: dict[str, Any],
    run_id: str,
    task_id: str,
    claim: str,
    actor: str,
    runtime: str,
    trust_tier: str,
    receipts: list[dict[str, Any]],
    ci_run_id: str | None = None,
) -> dict[str, Any]:
    """Assemble receipts without treating their status as a gate decision."""
    repository, source = discover_context(
        repo_root, policy=policy, claim=claim, ci_run_id=ci_run_id
    )
    claim_policy = policy["claims"][claim]
    bundle = {
        "schema_version": 1,
        "run_id": run_id,
        "task_id": task_id,
        "repository": repository,
        "actor": actor,
        "runtime": runtime,
        "claim": claim,
        "trust_tier": trust_tier,
        "source": source,
        "acceptance": {
            "required_evidence": list(claim_policy["required_evidence"]),
            "require_full_trust": bool(claim_policy.get("require_full_trust")),
        },
        "receipts": receipts,
    }
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle


def _validate_schema(bundle: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"schema:{'/'.join(str(item) for item in error.absolute_path)}:{error.message}"
        for error in sorted(
            validator.iter_errors(bundle), key=lambda item: list(item.path)
        )
    ]


def _receipt_scope_errors(receipt: dict[str, Any], bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if receipt.get("task_id") != bundle.get("task_id"):
        errors.append("cross_scope:task_id")
    receipt_repo = receipt.get("repository", {})
    bundle_repo = bundle.get("repository", {})
    for field in ("repo_id", "branch"):
        if receipt_repo.get(field) != bundle_repo.get(field):
            errors.append(f"cross_scope:{field}")
    if receipt_repo.get("worktree_id") != bundle_repo.get("worktree_id"):
        shared_ci_run = receipt_repo.get("ci_run_id")
        if not shared_ci_run or shared_ci_run != bundle_repo.get("ci_run_id"):
            errors.append("cross_scope:worktree_id")
    source = receipt.get("source", {})
    bundle_source = bundle.get("source", {})
    for field in (
        "head_sha",
        "material_hash",
        "task_diff_hash",
        "policy_hash",
        "command_set_hash",
    ):
        if source.get(field) != bundle_source.get(field):
            errors.append(f"stale_receipt:{field}")
    return errors


def _verify_receipt(
    receipt: dict[str, Any], bundle: dict[str, Any], policy: dict[str, Any]
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    degradations: list[str] = []
    digest = receipt.get("receipt_digest")
    content = {key: value for key, value in receipt.items() if key != "receipt_digest"}
    if digest != canonical_digest(content):
        errors.append(f"tampered_receipt:{receipt.get('receipt_id', '<unknown>')}")
    errors.extend(_receipt_scope_errors(receipt, bundle))

    kind = str(receipt.get("evidence_kind", ""))
    producer = str(receipt.get("producer", ""))
    kind_policy = policy.get("evidence_kinds", {}).get(kind)
    if not isinstance(kind_policy, dict):
        errors.append(f"unknown_evidence_kind:{kind}")
        return errors, degradations
    if producer not in kind_policy.get("authorized_producers", []):
        errors.append(f"unauthorized_producer:{kind}:{producer}")
    command = str(receipt.get("command", ""))
    families = [str(item) for item in kind_policy.get("command_families", [])]
    if not any(command.startswith(family) for family in families):
        errors.append(f"command_not_authorized:{kind}")

    status = receipt.get("status")
    if status == "fail":
        errors.append(f"failed_receipt:{kind}")
    elif status in {"skip", "unavailable"}:
        if not str(receipt.get("skip_reason") or "").strip():
            errors.append(f"missing_skip_reason:{kind}")
        if not str(receipt.get("follow_up") or "").strip():
            errors.append(f"missing_follow_up:{kind}")
        degradations.append(f"{status}_receipt:{kind}")
    elif status == "pass" and receipt.get("exit_code") != 0:
        errors.append(f"failed_reported_as_pass:{kind}")
    return errors, degradations


def verify_bundle(
    *,
    bundle: dict[str, Any],
    repo_root: Path,
    policy: dict[str, Any],
    schema: dict[str, Any],
    check_current_source: bool = True,
) -> VerificationResult:
    """Verify integrity, freshness, completeness, authorization, and outcome."""
    errors = _validate_schema(bundle, schema)
    degradations: list[str] = []
    if errors:
        return VerificationResult("STOP", False, tuple(sorted(set(errors))), ())

    content = {key: value for key, value in bundle.items() if key != "bundle_digest"}
    if bundle["bundle_digest"] != canonical_digest(content):
        errors.append("tampered_bundle")

    claim = str(bundle["claim"])
    expected_claim_policy = policy["claims"][claim]
    if bundle["acceptance"]["required_evidence"] != list(
        expected_claim_policy["required_evidence"]
    ):
        errors.append("acceptance_policy_drift:required_evidence")
    if bundle["acceptance"]["require_full_trust"] != bool(
        expected_claim_policy.get("require_full_trust")
    ):
        errors.append("acceptance_policy_drift:require_full_trust")
    expected_command_hash = command_set_hash(policy, claim)
    source = bundle["source"]
    if source["policy_hash"] != canonical_digest(policy):
        errors.append("policy_drift")
    if source["command_set_hash"] != expected_command_hash:
        errors.append("command_set_drift")

    if check_current_source:
        current_repo, current_source = discover_context(
            repo_root,
            policy=policy,
            claim=claim,
            ci_run_id=bundle["repository"].get("ci_run_id"),
        )
        if current_repo["repo_id"] != bundle["repository"]["repo_id"]:
            errors.append("cross_scope:repo_id")
        for field in (
            "head_sha",
            "material_hash",
            "task_diff_hash",
            "policy_hash",
            "command_set_hash",
        ):
            if current_source[field] != source[field]:
                errors.append(f"stale_bundle:{field}")

    receipts = bundle["receipts"]
    receipt_ids = [str(receipt["receipt_id"]) for receipt in receipts]
    if len(receipt_ids) != len(set(receipt_ids)):
        errors.append("duplicate_receipt_id")
    observed: dict[str, int] = {}
    for receipt in receipts:
        receipt_errors, receipt_degradations = _verify_receipt(receipt, bundle, policy)
        errors.extend(receipt_errors)
        degradations.extend(receipt_degradations)
        kind = str(receipt.get("evidence_kind", ""))
        observed[kind] = observed.get(kind, 0) + 1

    required = list(bundle["acceptance"]["required_evidence"])
    for kind in required:
        if observed.get(kind, 0) == 0:
            errors.append(f"missing_receipt:{kind}")

    trust_tier = str(bundle["trust_tier"])
    tier_policy = policy.get("trust_tiers", {}).get(trust_tier)
    if not isinstance(tier_policy, dict):
        errors.append(f"unsupported_trust_tier:{trust_tier}")
    else:
        expected_attestation = tier_policy.get("execution_attestation")
        for receipt in receipts:
            if receipt.get("execution_attestation") != expected_attestation:
                errors.append(
                    f"attestation_mismatch:{receipt.get('receipt_id', '<unknown>')}"
                )
        maximum = tier_policy.get("maximum_outcome")
        if maximum == "STOP":
            errors.append(f"untrusted_execution:{trust_tier}")
        elif maximum == "DEGRADED":
            degradations.append(f"trust_tier:{trust_tier}")

    if claim == "ready_to_merge" and (source["dirty"] or source["untracked_paths"]):
        errors.append("dirty_source_for_full_claim")
    if errors:
        return VerificationResult(
            "STOP", False, tuple(sorted(set(errors))), tuple(sorted(set(degradations)))
        )
    if degradations:
        return VerificationResult(
            "DEGRADED",
            False,
            (),
            tuple(sorted(set(degradations))),
        )
    return VerificationResult("ADMIT", True, (), ())
