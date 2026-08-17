"""Run exact-cover CodeRabbit leaves sequentially with bounded backoff."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_DATE = os.environ.get(
    "CODERABBIT_CAMPAIGN_DATE", datetime.now(UTC).strftime("%Y%m%d")
)
OUT = ROOT / "reports" / "quality" / "coderabbit" / CAMPAIGN_DATE
MATRIX_PATH = OUT / "01-scope-matrix.json"
PROGRESS_PATH = OUT / "progress.json"
BLOCKERS_PATH = OUT / "BLOCKERS.md"
PROMPT_PATH = OUT / "02-review-prompt.md"
CODERABBIT = (
    os.environ.get("CODERABBIT_BIN")
    or shutil.which("coderabbit")
    or "/home/fedor/.local/bin/coderabbit"
)
REVIEW_TIMEOUT_SECONDS = int(os.environ.get("CODERABBIT_REVIEW_TIMEOUT", "600"))
SLEEP_SECONDS = float(os.environ.get("CODERABBIT_SLEEP", "15"))
DEFAULT_RATE_LIMIT_BACKOFF = "1800,1800,1800"
DEFAULT_ERROR_BACKOFF = "20,40"
_WAIT_TIME_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)\b",
    re.IGNORECASE,
)


def now() -> str:
    return datetime.now(UTC).isoformat()


def parse_backoff_schedule(raw: str, *, default: str) -> tuple[float, ...]:
    """Parse a comma-separated positive-second backoff schedule."""
    text = (raw or "").strip() or default
    values: list[float] = []
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        value = float(token)
        if value <= 0:
            raise ValueError(f"backoff seconds must be positive, got {token!r}")
        values.append(value)
    if not values:
        raise ValueError("backoff schedule is empty")
    return tuple(values)


def parse_wait_time_to_seconds(text: str) -> float | None:
    """Convert a CodeRabbit waitTime token such as ``30 minutes`` to seconds."""
    match = _WAIT_TIME_RE.search((text or "").strip())
    if match is None:
        return None
    value = float(match.group("value"))
    unit = match.group("unit").casefold()
    if unit.startswith("h"):
        return value * 3600
    if unit.startswith("m"):
        return value * 60
    return value


def extract_rate_limit_wait_seconds(output: str) -> float | None:
    """Read waitTime from a CodeRabbit rate_limit JSON event, if present."""
    waits: list[float] = []
    for line in (output or "").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        metadata = event.get("metadata")
        wait_raw = None
        if isinstance(metadata, dict):
            wait_raw = metadata.get("waitTime")
        if wait_raw is None:
            wait_raw = event.get("waitTime")
        if wait_raw is None:
            continue
        parsed = parse_wait_time_to_seconds(str(wait_raw))
        if parsed is not None:
            waits.append(parsed)
    return max(waits) if waits else None


def has_review_completion(output: str) -> bool:
    """True when the agent log contains a terminal review_completed event."""
    for line in (output or "").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(event, dict)
            and event.get("type") == "complete"
            and event.get("status") == "review_completed"
        ):
            return True
    return False


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def save_progress(progress: dict[str, Any]) -> None:
    progress["updated_utc"] = now()
    PROGRESS_PATH.write_text(
        json.dumps(progress, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def record_blocker(leaf: dict[str, Any], kind: str, detail: str) -> None:
    if not BLOCKERS_PATH.exists():
        BLOCKERS_PATH.write_text(
            "# CodeRabbit campaign blockers\n\n"
            "Each entry requires GitHub reconciliation before closeout.\n\n",
            encoding="utf-8",
        )
    with BLOCKERS_PATH.open("a", encoding="utf-8") as stream:
        stream.write(
            f"## {leaf['id']} — {kind}\n\n"
            f"- UTC: `{now()}`\n"
            f"- Wave: `{leaf['wave']}`\n"
            f"- Files: `{leaf['files']}`\n"
            f"- Detail: {detail}\n"
            f"- GitHub issue: pending reconciliation\n\n"
        )


def manifest_files(leaf: dict[str, Any]) -> list[str]:
    manifest = ROOT / str(leaf["file_list"])
    paths = [line for line in manifest.read_text(encoding="utf-8").splitlines() if line]
    expected = int(leaf["files"])
    if len(paths) != expected:
        raise RuntimeError(
            f"{leaf['id']}: manifest count {len(paths)} != matrix count {expected}"
        )
    if len(paths) > 300:
        raise RuntimeError(f"{leaf['id']}: {len(paths)} files exceeds hard cap 300")
    return paths


def run_checked(cmd: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def materialize_leaf(base_sha: str, paths: list[str], target: Path) -> None:
    archive_env = os.environ.copy()
    archive_env["GIT_LFS_SKIP_SMUDGE"] = "1"
    archive = subprocess.run(
        ["git", "-C", str(ROOT), "archive", "--format=tar", base_sha, "--", *paths],
        env=archive_env,
        check=True,
        capture_output=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as bundle:
        bundle.extractall(target, filter="data")

    git_env = os.environ.copy()
    git_env["GIT_LFS_SKIP_SMUDGE"] = "1"
    git_env["GIT_AUTHOR_NAME"] = "BioETL CR-FULL Audit"
    git_env["GIT_AUTHOR_EMAIL"] = "audit@local.invalid"
    git_env["GIT_COMMITTER_NAME"] = "BioETL CR-FULL Audit"
    git_env["GIT_COMMITTER_EMAIL"] = "audit@local.invalid"
    run_checked(["git", "init", "-q"], target, git_env)
    run_checked(
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://github.com/SatoryKono/BioactivityDataAcquisition.git",
        ],
        target,
        git_env,
    )
    run_checked(
        ["git", "commit", "--allow-empty", "-qm", "audit leaf base"], target, git_env
    )
    run_checked(["git", "branch", "main"], target, git_env)
    run_checked(["git", "config", "coderabbit.baseBranch", "main"], target, git_env)
    run_checked(["git", "add", "--all"], target, git_env)
    run_checked(["git", "commit", "-qm", "materialize audit leaf"], target, git_env)
    run_checked(["git", "branch", "-M", "audit-leaf"], target, git_env)


def _structured_error_type(output: str) -> str | None:
    """Return the last JSON errorType, ignoring finding/file payload text."""
    error_type: str | None = None
    for line in (output or "").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "error":
            continue
        raw = str(event.get("errorType") or "").strip()
        if raw:
            error_type = raw
    return error_type


def classify_output(return_code: int, output: str) -> tuple[str, str]:
    error_type = (_structured_error_type(output) or "").casefold()
    completed = has_review_completion(output)
    # A completed review wins over payload text such as network_rate_limit_helpers.py
    # or exception messages that contain "Rate limit exceeded".
    if error_type == "rate_limit" and not completed:
        wait = extract_rate_limit_wait_seconds(output)
        if wait is None:
            return "rate_limit", "CodeRabbit rate limit"
        return "rate_limit", f"CodeRabbit rate limit (waitTime={int(wait)}s)"
    lowered = output.lower()
    if "all files are ignored" in lowered or "all_files_ignored" in lowered:
        return "all_files_ignored", "CodeRabbit reported all files ignored"
    if (
        error_type in {"not_authenticated", "unauthenticated"}
        or "not_authenticated" in lowered
        or "not authenticated" in lowered
    ) and not completed:
        return "auth_error", "CodeRabbit authentication failed"
    if (
        error_type in {"websocket", "connection"}
        or "websocket" in lowered
        or "socket hang up" in lowered
        or "econnreset" in lowered
    ) and not completed:
        return "connection_error", "CodeRabbit connection/WebSocket failure"
    if return_code != 0 and not completed:
        return "error", f"CodeRabbit exit code {return_code}"
    if not completed:
        return "missing_output", "CodeRabbit exited 0 without review_completed"
    return "ok", ""


def run_leaf(leaf: dict[str, Any], base_sha: str) -> dict[str, Any]:
    leaf_id = str(leaf["id"])
    wave = str(leaf["wave"])
    log_path = OUT / f"review_{wave}_{leaf_id}.log"
    paths = manifest_files(leaf)
    started = time.monotonic()
    env = os.environ.copy()
    bin_dir = Path(CODERABBIT).parent
    if str(bin_dir) not in {"", "."}:
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    env["GIT_LFS_SKIP_SMUDGE"] = "1"

    with tempfile.TemporaryDirectory(prefix=f"bioetl-cr-{leaf_id[:32]}-") as tmp:
        target = Path(tmp)
        try:
            materialize_leaf(base_sha, paths, target)
        except (OSError, subprocess.CalledProcessError, tarfile.TarError) as exc:
            output = f"LEAF_MATERIALIZATION_FAILED: {exc}\n"
            log_path.write_text(output, encoding="utf-8")
            return {
                "id": leaf_id,
                "wave": wave,
                "files": len(paths),
                "status": "materialization_error",
                "reason": str(exc),
                "log": str(log_path.relative_to(ROOT)),
                "elapsed_s": round(time.monotonic() - started, 1),
            }

        command = [
            CODERABBIT,
            "review",
            "--base",
            "main",
            "--dir",
            ".",
            "--agent",
            "-c",
            str(ROOT / "AGENTS.md"),
            str(ROOT / ".coderabbit.yaml"),
            str(PROMPT_PATH),
        ]
        try:
            process = subprocess.run(
                command,
                cwd=target,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=REVIEW_TIMEOUT_SECONDS,
                check=False,
            )
            output = process.stdout or ""
            if process.stderr:
                output += "\n" + process.stderr
            log_path.write_text(output, encoding="utf-8")
            status, reason = classify_output(process.returncode, output)
            return {
                "id": leaf_id,
                "wave": wave,
                "files": len(paths),
                "status": status,
                "reason": reason,
                "exit_code": process.returncode,
                "log": str(log_path.relative_to(ROOT)),
                "bytes": len(output.encode("utf-8")),
                "elapsed_s": round(time.monotonic() - started, 1),
                "command": command,
            }
        except subprocess.TimeoutExpired as exc:
            partial = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            log_path.write_text(
                partial + f"\nTIMEOUT after {REVIEW_TIMEOUT_SECONDS}s\n",
                encoding="utf-8",
            )
            return {
                "id": leaf_id,
                "wave": wave,
                "files": len(paths),
                "status": "timeout",
                "reason": f"timeout after {REVIEW_TIMEOUT_SECONDS}s",
                "log": str(log_path.relative_to(ROOT)),
                "elapsed_s": round(time.monotonic() - started, 1),
            }


def selected_leaves(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    raw_leaves = matrix.get("leaves", [])
    leaves = [leaf for leaf in raw_leaves if isinstance(leaf, dict)]
    wave = os.environ.get("CR_WAVE")
    ids = {item for item in os.environ.get("CR_LEAVES", "").split(",") if item}
    if wave:
        leaves = [leaf for leaf in leaves if leaf.get("wave") == wave]
    if ids:
        leaves = [leaf for leaf in leaves if leaf.get("id") in ids]
    return sorted(leaves, key=lambda leaf: (str(leaf["wave"]), str(leaf["id"])))


def main() -> int:
    matrix = load_json(MATRIX_PATH, {})
    if matrix.get("coverage_ok") is not True:
        raise RuntimeError("refusing to run a non-exact scope matrix")
    base_sha = str(matrix["base_sha"])
    leaves = selected_leaves(matrix)
    progress = load_json(
        PROGRESS_PATH,
        {
            "campaign": matrix["campaign"],
            "base_sha": base_sha,
            "started_utc": now(),
            "results": {},
        },
    )
    results = progress.setdefault("results", {})
    if not isinstance(results, dict):
        raise TypeError("progress.results must be an object")

    rate_limit_backoff = parse_backoff_schedule(
        os.environ.get("CODERABBIT_RATE_LIMIT_BACKOFF", ""),
        default=DEFAULT_RATE_LIMIT_BACKOFF,
    )
    error_backoff = parse_backoff_schedule(
        os.environ.get("CODERABBIT_ERROR_BACKOFF", ""),
        default=DEFAULT_ERROR_BACKOFF,
    )
    print(
        f"campaign={matrix['campaign']} base={base_sha} planned={len(leaves)} "
        f"sequential=true rate_limit_backoff={rate_limit_backoff} "
        f"error_backoff={error_backoff}",
        flush=True,
    )
    for index, leaf in enumerate(leaves, 1):
        leaf_id = str(leaf["id"])
        prior = results.get(leaf_id)
        if isinstance(prior, dict) and prior.get("status") == "ok":
            print(f"[{index}/{len(leaves)}] SKIP completed {leaf_id}", flush=True)
            continue
        print(
            f"[{index}/{len(leaves)}] RUN wave={leaf['wave']} leaf={leaf_id} files={leaf['files']}",
            flush=True,
        )
        result = run_leaf(leaf, base_sha)
        results[leaf_id] = result
        save_progress(progress)
        print(
            f"[{index}/{len(leaves)}] RESULT leaf={leaf_id} status={result['status']} "
            f"elapsed={result['elapsed_s']}s bytes={result.get('bytes', 0)}",
            flush=True,
        )

        if result["status"] == "rate_limit":
            log_path = ROOT / str(result.get("log") or "")
            parsed_wait = extract_rate_limit_wait_seconds(
                log_path.read_text(encoding="utf-8", errors="replace")
                if log_path.is_file()
                else ""
            )
            waits = (
                (parsed_wait,) + rate_limit_backoff[1:]
                if parsed_wait is not None
                else rate_limit_backoff
            )
            record_blocker(leaf, "rate_limit", str(result["reason"]))
            for wait_seconds in waits:
                print(
                    f"[{index}/{len(leaves)}] RATE_LIMIT_WAIT leaf={leaf_id} "
                    f"after={int(wait_seconds)}s",
                    flush=True,
                )
                time.sleep(wait_seconds)
                print(
                    f"[{index}/{len(leaves)}] RETRY leaf={leaf_id} after={int(wait_seconds)}s",
                    flush=True,
                )
                retry = run_leaf(leaf, base_sha)
                results[leaf_id] = retry
                save_progress(progress)
                print(
                    f"[{index}/{len(leaves)}] RETRY_RESULT leaf={leaf_id} status={retry['status']}",
                    flush=True,
                )
                if retry["status"] != "rate_limit":
                    break
            if results[leaf_id]["status"] == "rate_limit":
                print(
                    "RATE_LIMIT_PERSISTS: stopping this wave for bounded backoff",
                    flush=True,
                )
                break
        elif result["status"] in {"connection_error", "error", "missing_output"}:
            record_blocker(leaf, str(result["status"]), str(result["reason"]))
            for wait_seconds in error_backoff:
                time.sleep(wait_seconds)
                print(
                    f"[{index}/{len(leaves)}] RETRY leaf={leaf_id} after={int(wait_seconds)}s",
                    flush=True,
                )
                retry = run_leaf(leaf, base_sha)
                results[leaf_id] = retry
                save_progress(progress)
                print(
                    f"[{index}/{len(leaves)}] RETRY_RESULT leaf={leaf_id} status={retry['status']}",
                    flush=True,
                )
                if retry["status"] == "ok":
                    break
                if retry["status"] == "rate_limit":
                    break
        elif result["status"] == "all_files_ignored":
            record_blocker(leaf, "all_files_ignored", str(result["reason"]))
        elif result["status"] in {
            "auth_error",
            "timeout",
            "materialization_error",
        }:
            record_blocker(leaf, str(result["status"]), str(result["reason"]))

        if results[leaf_id]["status"] == "rate_limit":
            print(
                "RATE_LIMIT_PERSISTS: stopping this wave for bounded backoff",
                flush=True,
            )
            break

        time.sleep(SLEEP_SECONDS)

    counts = Counter(
        str(item.get("status", "unknown"))
        for item in results.values()
        if isinstance(item, dict)
    )
    summary = {
        "campaign": matrix["campaign"],
        "base_sha": base_sha,
        "updated_utc": now(),
        "counts": dict(sorted(counts.items())),
        "results": results,
    }
    (OUT / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"SUMMARY {dict(sorted(counts.items()))}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
