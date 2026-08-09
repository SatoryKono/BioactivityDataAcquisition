#!/usr/bin/env python3
"""Run optional AgentDebugX and ProofAgent tools through a safe advisory seam.

The vendor packages are never imported into the BioETL process. Every execution
uses a fresh subprocess, a bounded timeout, a secret-stripped environment, and
an output directory confined to ``reports/ai/agent-tools``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from memory.proof import canonical_digest, command_set_hash, load_policy
from scripts.engineering.common.repo_paths import (
    ensure_path_within_root,
    ensure_safe_cli_argv,
)

ROOT: Final[Path] = Path(__file__).resolve().parents[3]
REPORT_ROOT_RELATIVE: Final[Path] = Path("reports/ai/agent-tools")
INPUT_ROOTS: Final[tuple[Path, ...]] = (
    Path("reports/ai/agent-tools/inputs"),
    Path("tests/fixtures/agent-tools"),
)
TASK_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$"
)
SECRET_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:AUTH|CREDENTIAL|KEY|PASSWORD|SECRET|TOKEN)", re.IGNORECASE
)
SECRET_TEXT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)(api[_-]?key|authorization|credential|password|secret|token)"
        r"\s*[:=]\s*([^\s,;]+)"
    ),
    re.compile(r"\b(?:gh[opsu]_|sk-[A-Za-z0-9_-]{8,})[A-Za-z0-9_-]+\b"),
)
EXIT_OK: Final[int] = 0
EXIT_USAGE: Final[int] = 2
EXIT_UNAVAILABLE: Final[int] = 3
EXIT_INCOMPATIBLE: Final[int] = 4
EXIT_TIMEOUT: Final[int] = 5
EXIT_VENDOR_FAILURE: Final[int] = 6
EXIT_MALFORMED: Final[int] = 7
DEFAULT_TIMEOUT_SECONDS: Final[int] = 90
MAX_TIMEOUT_SECONDS: Final[int] = 600
DENY_GLOBS: Final[str] = "**/.env,**/.env.*,**/secrets/**,**/*credential*"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Pinned identity and invocation contract for one optional tool."""

    name: str
    distribution: str
    expected_version: str
    executable: str
    report_subdir: str


TOOLS: Final[dict[str, ToolSpec]] = {
    "agentdebugx": ToolSpec(
        name="AgentDebugX",
        distribution="agentdebugx",
        expected_version="0.3.1",
        executable="agentdebug",
        report_subdir="agentdebugx",
    ),
    "proofagent": ToolSpec(
        name="ProofAgent Harness",
        distribution="proofagent-harness",
        expected_version="0.11.0",
        executable="proof",
        report_subdir="proofagent",
    ),
}

ADVISORY_POLICY: Final[dict[str, Any]] = {
    "schema_version": 1,
    "mode": "advisory",
    "network": "disabled",
    "uploads": "disabled",
    "llm_assessment": "disabled",
    "lifecycle_authority": False,
    "may_override_core_checks": False,
    "input_roots": [path.as_posix() for path in INPUT_ROOTS],
    "output_root": REPORT_ROOT_RELATIVE.as_posix(),
}


def _redact(text: str) -> str:
    """Remove common secret forms from captured vendor output."""
    redacted = text
    for pattern in SECRET_TEXT_PATTERNS:
        if pattern.pattern.lower().startswith("(?i)bearer"):
            redacted = pattern.sub("Bearer [REDACTED]", redacted)
        elif pattern.groups >= 2:
            redacted = pattern.sub(r"\1=[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if SECRET_NAME_PATTERN.search(str(key))
                else _redact_payload(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, str):
        return _redact(value)
    return value


def _write_protected(path: Path, content: str) -> None:
    """Write a confined attachment and restrict it to the current user."""
    output_root = ensure_path_within_root(ROOT / REPORT_ROOT_RELATIVE, ROOT)
    safe_path = ensure_path_within_root(path, output_root)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(content, encoding="utf-8")
    safe_path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _output_dir(tool: ToolSpec, task_id: str) -> Path:
    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise ValueError(
            "task-id must start with an alphanumeric character and contain only "
            "letters, digits, '_' or '-' (maximum 80 characters)"
        )
    output_root = ensure_path_within_root(ROOT / REPORT_ROOT_RELATIVE, ROOT)
    destination = ensure_path_within_root(
        output_root / tool.report_subdir / task_id, output_root
    )
    destination.mkdir(parents=True, exist_ok=True)
    destination.chmod(stat.S_IRWXU)
    return destination


def _resolve_input(value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if candidate.is_symlink():
        raise ValueError("symbolic-link inputs are not allowed")
    resolved = candidate.resolve(strict=True)
    allowed = [ensure_path_within_root(ROOT / path, ROOT) for path in INPUT_ROOTS]
    if not any(root == resolved or root in resolved.parents for root in allowed):
        raise ValueError(
            "input must be under reports/ai/agent-tools/inputs or "
            "tests/fixtures/agent-tools"
        )
    if resolved.name.lower() == ".env" or resolved.name.lower().startswith(".env."):
        raise ValueError(".env inputs are forbidden")
    if not resolved.is_file():
        raise ValueError(f"input is not a file: {resolved}")
    return resolved


def _executable_path(spec: ToolSpec) -> Path | None:
    suffix = ".exe" if os.name == "nt" else ""
    # Do not resolve the Python launcher first: POSIX venv interpreters are
    # commonly symlinks to the system Python, while console scripts live beside
    # the symlink inside ``venv/bin``.
    adjacent = Path(sys.executable).parent / f"{spec.executable}{suffix}"
    if adjacent.is_file():
        return adjacent
    discovered = shutil.which(spec.executable)
    return Path(discovered).resolve() if discovered else None


def _tool_status(spec: ToolSpec) -> dict[str, Any]:
    try:
        version = importlib.metadata.version(spec.distribution)
    except importlib.metadata.PackageNotFoundError:
        version = None
    executable = _executable_path(spec)
    if version is None or executable is None:
        state = "UNAVAILABLE"
        exit_code = EXIT_UNAVAILABLE
    elif version != spec.expected_version:
        state = "INCOMPATIBLE"
        exit_code = EXIT_INCOMPATIBLE
    else:
        state = "AVAILABLE"
        exit_code = EXIT_OK
    return {
        "name": spec.name,
        "distribution": spec.distribution,
        "expected_version": spec.expected_version,
        "installed_version": version,
        "executable": str(executable) if executable else None,
        "state": state,
        "exit_code": exit_code,
    }


def _source_context(
    materials: tuple[Path, ...] = (), *, scope: str | None = None
) -> dict[str, Any]:
    """Build a bounded advisory identity with Proof-or-Stop-compatible fields.

    The canonical gate hashes every material file and the complete binary task
    diff. That is appropriate for an authoritative receipt but can be expensive
    on LFS-heavy worktrees. This producer is advisory, so it binds to the HEAD
    tree plus changed/untracked path inventory and labels the weaker mode
    explicitly. The artifact cannot be mistaken for a Proof-or-Stop receipt.
    """
    policy_path = ROOT / "configs/quality/proof_or_stop_policy.yaml"
    policy = load_policy(policy_path)

    def git_run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "git",
                "-c",
                "filter.lfs.process=",
                "-c",
                "filter.lfs.required=false",
                "-c",
                "filter.lfs.clean=cat",
                "-c",
                "filter.lfs.smudge=cat",
                "-C",
                str(ROOT),
                *args,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

    def git_text(*args: str) -> str:
        completed = git_run(*args)
        if completed.returncode != 0:
            raise OSError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
        return completed.stdout.strip()

    head_sha = git_text("rev-parse", "HEAD")
    tree_sha = git_text("rev-parse", "HEAD^{tree}")
    branch = git_text("branch", "--show-current") or "detached"
    # This producer is advisory and intentionally avoids any working-tree scan.
    # On LFS-heavy mounted worktrees, both status and untracked enumeration can
    # exceed the entire vendor timeout before the vendor process starts. The
    # weaker binding is explicit and relies on HEAD plus reviewed materials.
    policy_hash = canonical_digest(policy)
    bound_materials = []
    for path in materials:
        safe_path = ensure_path_within_root(path, ROOT)
        bound_materials.append(
            {
                "path": safe_path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(safe_path.read_bytes()).hexdigest(),
            }
        )
    dirty: bool | None = None
    repository = {
        "repo_id": ROOT.name.lower(),
        "branch": branch,
        "worktree_id": hashlib.sha256(str(ROOT.resolve()).encode()).hexdigest()[:16],
        "ci_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    source = {
        "head_sha": head_sha,
        "material_hash": hashlib.sha256(tree_sha.encode()).hexdigest(),
        "task_diff_hash": canonical_digest(
            {
                "tracked_dirty": dirty,
                "tracked_worktree_state": "not-collected",
                "untracked_inventory": "not-collected",
                "bound_materials": bound_materials,
                "scope": scope,
                "policy_hash": policy_hash,
            }
        ),
        "policy_hash": policy_hash,
        "command_set_hash": command_set_hash(policy, "ready_to_merge"),
        "dirty": dirty,
        "tracked_worktree_state": "not-collected",
        "untracked_paths": [],
        "untracked_inventory": "not-collected",
        "bound_materials": bound_materials,
        "scope": scope,
        "binding_mode": "bounded-advisory-v1",
        "changed_path_inventory": "not-collected",
        "head_tree_sha": tree_sha,
    }
    return {
        "repository": repository,
        "source": source,
        "proof_or_stop_policy": {
            "path": policy_path.relative_to(ROOT).as_posix(),
            "sha256": canonical_digest(policy),
        },
    }


def _safe_environment(output_dir: Path) -> dict[str, str]:
    keep = {
        "COMSPEC",
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "PYTHONIOENCODING",
        "PYTHONUTF8",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "VIRTUAL_ENV",
        "WINDIR",
    }
    env = {
        name: value
        for name, value in os.environ.items()
        if name in keep and not SECRET_NAME_PATTERN.search(name)
    }
    sandbox_home = output_dir / "sandbox-home"
    sandbox_home.mkdir(parents=True, exist_ok=True)
    sandbox_home.chmod(stat.S_IRWXU)
    env.update(
        {
            "HOME": str(sandbox_home),
            "USERPROFILE": str(sandbox_home),
            "XDG_CACHE_HOME": str(sandbox_home / "cache"),
            "XDG_CONFIG_HOME": str(sandbox_home / "config"),
            "XDG_DATA_HOME": str(sandbox_home / "data"),
            "DO_NOT_TRACK": "1",
            "LITELLM_LOCAL_MODEL_COST_MAP": "true",
            "LITELLM_TELEMETRY": "false",
            "PROOFAGENT_DISABLE_TELEMETRY": "1",
        }
    )
    return env


def _proof_verdict(payload: dict[str, Any]) -> str:
    certification = str(payload.get("certification") or "").upper()
    if certification == "GOLD":
        return "PASS"
    if certification == "SILVER":
        return "WARN"
    if certification in {"NEEDS_ENHANCEMENT", "NOT_READY", "INCOMPLETE"}:
        return "FAIL"
    return "UNAVAILABLE"


def _agentdebug_verdict(payload: dict[str, Any]) -> str:
    root_cause = payload.get("root_cause")
    findings = payload.get("findings") or payload.get("failure_points")
    return "WARN" if root_cause or findings else "PASS"


def _summary(
    *,
    spec: ToolSpec,
    task_id: str,
    status: str,
    verdict: str,
    exit_code: int,
    duration_ms: int,
    command: list[str],
    identity: dict[str, Any],
    detail: str | None = None,
    vendor_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "task_id": task_id,
        "producer": spec.report_subdir,
        "status": status,
        "verdict": verdict,
        "advisory": True,
        "lifecycle_authority": False,
        "may_override_core_checks": False,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "command": command,
        "tool": _tool_status(spec),
        "adapter_policy": {
            **ADVISORY_POLICY,
            "sha256": canonical_digest(ADVISORY_POLICY),
        },
        **identity,
    }
    source_binding = identity.get("source")
    payload["optional_evaluator_evidence"] = {
        "schema_version": 1,
        "evidence_kind": "review",
        "producer": f"optional_{spec.report_subdir}",
        "vendor_verdict": verdict,
        "receipt_eligible": False,
        "lifecycle_authority": False,
        "source_binding": source_binding if isinstance(source_binding, dict) else None,
    }
    if detail:
        payload["detail"] = _redact(detail)
    if vendor_payload is not None:
        payload["vendor_result"] = _redact_payload(vendor_payload)
    return payload


def _emit_result(output_dir: Path, payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _write_protected(output_dir / "summary.json", rendered)
    print(rendered, end="")


def _run(
    *,
    spec: ToolSpec,
    task_id: str,
    command_builder: Any,
    timeout: int,
    identity_materials: tuple[Path, ...] = (),
    identity_scope: str | None = None,
) -> int:
    started = time.monotonic()
    output_dir = _output_dir(spec, task_id)
    try:
        identity = _source_context(identity_materials, scope=identity_scope)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        payload = _summary(
            spec=spec,
            task_id=task_id,
            status="SOURCE_IDENTITY_FAILURE",
            verdict="UNAVAILABLE",
            exit_code=EXIT_VENDOR_FAILURE,
            duration_ms=0,
            command=[],
            identity={},
            detail=str(exc),
        )
        _emit_result(output_dir, payload)
        return EXIT_VENDOR_FAILURE

    status = _tool_status(spec)
    if status["state"] != "AVAILABLE":
        payload = _summary(
            spec=spec,
            task_id=task_id,
            status=status["state"],
            verdict="UNAVAILABLE",
            exit_code=int(status["exit_code"]),
            duration_ms=0,
            command=[],
            identity=identity,
            detail=f"Install the '{spec.report_subdir}' optional dependency.",
        )
        _emit_result(output_dir, payload)
        return int(status["exit_code"])

    vendor_output = output_dir / "vendor-output.json"
    command = ensure_safe_cli_argv(
        command_builder(Path(str(status["executable"])), vendor_output)
    )
    try:
        completed = subprocess.run(
            command,
            cwd=output_dir,
            env=_safe_environment(output_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.monotonic() - started) * 1000)
        _write_protected(output_dir / "stdout.txt", _redact(exc.stdout or ""))
        _write_protected(output_dir / "stderr.txt", _redact(exc.stderr or ""))
        payload = _summary(
            spec=spec,
            task_id=task_id,
            status="TIMEOUT",
            verdict="UNAVAILABLE",
            exit_code=EXIT_TIMEOUT,
            duration_ms=duration_ms,
            command=command,
            identity=identity,
            detail=f"vendor subprocess exceeded {timeout} seconds",
        )
        _emit_result(output_dir, payload)
        return EXIT_TIMEOUT

    duration_ms = round((time.monotonic() - started) * 1000)
    _write_protected(output_dir / "stdout.txt", _redact(completed.stdout))
    _write_protected(output_dir / "stderr.txt", _redact(completed.stderr))
    if completed.returncode not in (
        {0} if spec.report_subdir == "agentdebugx" else {0, 1}
    ):
        payload = _summary(
            spec=spec,
            task_id=task_id,
            status="VENDOR_FAILURE",
            verdict="UNAVAILABLE",
            exit_code=EXIT_VENDOR_FAILURE,
            duration_ms=duration_ms,
            command=command,
            identity=identity,
            detail=f"vendor exit code {completed.returncode}",
        )
        _emit_result(output_dir, payload)
        return EXIT_VENDOR_FAILURE

    try:
        raw_payload = json.loads(vendor_output.read_text(encoding="utf-8"))
        if not isinstance(raw_payload, dict):
            raise ValueError("vendor JSON must be an object")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        payload = _summary(
            spec=spec,
            task_id=task_id,
            status="MALFORMED_OUTPUT",
            verdict="UNAVAILABLE",
            exit_code=EXIT_MALFORMED,
            duration_ms=duration_ms,
            command=command,
            identity=identity,
            detail=str(exc),
        )
        _emit_result(output_dir, payload)
        return EXIT_MALFORMED

    safe_vendor_payload = _redact_payload(raw_payload)
    _write_protected(
        vendor_output,
        json.dumps(safe_vendor_payload, indent=2, sort_keys=True) + "\n",
    )
    verdict = (
        _agentdebug_verdict(raw_payload)
        if spec.report_subdir == "agentdebugx"
        else _proof_verdict(raw_payload)
    )
    payload = _summary(
        spec=spec,
        task_id=task_id,
        status="COMPLETED",
        verdict=verdict,
        exit_code=EXIT_OK,
        duration_ms=duration_ms,
        command=command,
        identity=identity,
        vendor_payload=raw_payload,
    )
    _emit_result(output_dir, payload)
    return EXIT_OK


def _doctor(tool: str) -> int:
    selected = list(TOOLS) if tool == "all" else [tool]
    statuses = [_tool_status(TOOLS[name]) for name in selected]
    payload = {
        "schema_version": 1,
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
            "platform": sys.platform,
        },
        "policy": {
            **ADVISORY_POLICY,
            "sha256": canonical_digest(ADVISORY_POLICY),
        },
        "tools": statuses,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return max(int(item["exit_code"]) for item in statuses)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safe optional adapters for AgentDebugX and ProofAgent."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    doctor = subcommands.add_parser("doctor", help="Report pinned tool availability.")
    doctor.add_argument(
        "--tool", choices=["all", *TOOLS], default="all", help="Tool to inspect."
    )

    debug = subcommands.add_parser(
        "debug", help="Run AgentDebugX in deterministic heuristic mode."
    )
    debug.add_argument("--task-id", required=True)
    debug.add_argument("--trajectory", required=True)
    debug.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, metavar="SECONDS"
    )

    evaluate = subcommands.add_parser(
        "evaluate", help="Run ProofAgent Tier-1 as advisory evidence."
    )
    evaluate.add_argument("--task-id", required=True)
    source = evaluate.add_mutually_exclusive_group(required=True)
    source.add_argument("--events", help="Normalized generic events JSONL.")
    source.add_argument(
        "--from-git", action="store_true", help="Screen current git changes."
    )
    evaluate.add_argument(
        "--scope", help="Required comma-separated in-scope globs for --from-git."
    )
    evaluate.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, metavar="SECONDS"
    )
    return parser


def _validated_timeout(value: int) -> int:
    if value < 1 or value > MAX_TIMEOUT_SECONDS:
        raise ValueError(f"timeout must be between 1 and {MAX_TIMEOUT_SECONDS} seconds")
    return value


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        return _doctor(args.tool)

    try:
        timeout = _validated_timeout(args.timeout)
        if args.command == "debug":
            trajectory = _resolve_input(args.trajectory)
            return _run(
                spec=TOOLS["agentdebugx"],
                task_id=args.task_id,
                timeout=timeout,
                identity_materials=(trajectory,),
                command_builder=lambda executable, output: [
                    str(executable),
                    "analyze",
                    str(trajectory),
                    "--mode",
                    "deterministic",
                    "--out",
                    str(output),
                ],
            )

        if args.from_git:
            if not args.scope or not args.scope.strip():
                raise ValueError("--scope is required with --from-git")

            def proof_command(executable: Path, output: Path) -> list[str]:
                return [
                    str(executable),
                    "session",
                    "--from-git",
                    "--workspace",
                    str(ROOT),
                    "--tool",
                    "generic",
                    "--scope",
                    args.scope,
                    "--deny",
                    DENY_GLOBS,
                    "--assess",
                    "never",
                    "--no-upload",
                    "--json",
                    str(output),
                    "--quiet",
                ]

        else:
            events = _resolve_input(args.events)

            def proof_command(executable: Path, output: Path) -> list[str]:
                return [
                    str(executable),
                    "session",
                    str(events),
                    "--tool",
                    "generic",
                    "--deny",
                    DENY_GLOBS,
                    "--assess",
                    "never",
                    "--no-upload",
                    "--json",
                    str(output),
                    "--quiet",
                ]

        return _run(
            spec=TOOLS["proofagent"],
            task_id=args.task_id,
            timeout=timeout,
            identity_materials=(() if args.from_git else (events,)),
            identity_scope=(args.scope if args.from_git else None),
            command_builder=proof_command,
        )
    except (OSError, ValueError) as exc:
        print(f"agent-tools: {_redact(str(exc))}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
