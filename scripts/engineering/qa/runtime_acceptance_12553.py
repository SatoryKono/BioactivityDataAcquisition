"""Capture issue 12553 commands without conflating test success with acceptance.

Each invocation preserves byte-for-byte stdout/stderr, exit status, argv and
the actual pre-run Git identity. Evidence is separate from the static inventory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import UTC, datetime

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "reports/audit-runs/12553-runtime-acceptance"


def git(*args: str) -> str:
    """Read Git identity without including environment values."""
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def capture(name: str, argv: list[str], timeout: int = 600) -> int:
    """Persist genuine command streams, including failed or timed-out runs."""
    if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name):
        raise ValueError("name must be lowercase ASCII letters/digits/hyphens")
    receipt = BUNDLE / f"{name}-command.json"
    if receipt.exists():
        raise FileExistsError(f"preserve previous run; choose another name: {receipt}")
    BUNDLE.mkdir(parents=True, exist_ok=True)
    metadata = {
        "argv": argv,
        "cwd": str(ROOT),
        "head_sha": git("rev-parse", "HEAD"),
        "tree_sha": git("rev-parse", "HEAD^{tree}"),
        "status_before": git("status", "--porcelain=v1", "--untracked-files=normal"),
        "started_utc": datetime.now(UTC).isoformat(),
        "timeout_seconds": timeout,
    }
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    with (BUNDLE / f"{name}-stdout.txt").open("wb") as out:
        with (BUNDLE / f"{name}-stderr.txt").open("wb") as err:
            try:
                result = subprocess.run(
                    argv,
                    cwd=ROOT,
                    env=env,
                    stdout=out,
                    stderr=err,
                    timeout=timeout,
                    check=False,
                )
                code = result.returncode
                metadata["timed_out"] = False
            except subprocess.TimeoutExpired:
                code = 124
                metadata["timed_out"] = True
    metadata.update(exit_code=code, finished_utc=datetime.now(UTC).isoformat())
    receipt.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (BUNDLE / f"{name}-exit-code.txt").write_text(f"{code}\n", encoding="ascii")
    print(f"{name}: exit={code}", flush=True)
    return code


def hashes() -> None:
    """Hash bundle bytes, excluding this manifest's unavoidable self-reference."""
    rows = {
        p.relative_to(BUNDLE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(BUNDLE.rglob("*"))
        if p.is_file() and p.name != "artifact-sha256.json"
    }
    (BUNDLE / "artifact-sha256.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    """Run one named command or refresh the evidence checksum manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.name == "hashes":
        hashes()
        return 0
    argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
    if not argv:
        parser.error("command required after --")
    return capture(args.name, argv, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
