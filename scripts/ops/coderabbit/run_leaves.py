"""Run exact-cover CodeRabbit leaves sequentially with bounded backoff."""

from __future__ import annotations

import io
import json
import os
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
CODERABBIT = os.environ.get("CODERABBIT_BIN", "/home/fedor/.local/bin/coderabbit")
REVIEW_TIMEOUT_SECONDS = int(os.environ.get("CODERABBIT_REVIEW_TIMEOUT", "600"))
SLEEP_SECONDS = float(os.environ.get("CODERABBIT_SLEEP", "5"))


def now() -> str:
    return datetime.now(UTC).isoformat()


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


def classify_output(return_code: int, output: str) -> tuple[str, str]:
    lowered = output.lower()
    if "rate_limit" in lowered or "rate limit" in lowered or "rate-limit" in lowered:
        return "rate_limit", "CodeRabbit rate limit"
    if "all files are ignored" in lowered or "all_files_ignored" in lowered:
        return "all_files_ignored", "CodeRabbit reported all files ignored"
    if "not_authenticated" in lowered or "not authenticated" in lowered:
        return "auth_error", "CodeRabbit authentication failed"
    if return_code != 0:
        return "error", f"CodeRabbit exit code {return_code}"
    return "ok", ""


def run_leaf(leaf: dict[str, Any], base_sha: str) -> dict[str, Any]:
    leaf_id = str(leaf["id"])
    wave = str(leaf["wave"])
    log_path = OUT / f"review_{wave}_{leaf_id}.log"
    paths = manifest_files(leaf)
    started = time.monotonic()
    env = os.environ.copy()
    env["PATH"] = f"/home/fedor/.local/bin:{env.get('PATH', '')}"
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

    print(
        f"campaign={matrix['campaign']} base={base_sha} planned={len(leaves)} sequential=true"
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
            record_blocker(leaf, "rate_limit", str(result["reason"]))
            for wait_seconds in (30, 60):
                time.sleep(wait_seconds)
                print(
                    f"[{index}/{len(leaves)}] RETRY leaf={leaf_id} after={wait_seconds}s",
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
        elif result["status"] == "all_files_ignored":
            record_blocker(leaf, "all_files_ignored", str(result["reason"]))
        elif result["status"] in {
            "auth_error",
            "error",
            "timeout",
            "materialization_error",
        }:
            record_blocker(leaf, str(result["status"]), str(result["reason"]))

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
