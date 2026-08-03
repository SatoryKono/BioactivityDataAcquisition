#!/usr/bin/env python3
"""Detect and reconcile Codex, Junie, and Devin runtime skill drift.

Codex is the propagation source for this operation. Junie remains an equal-peer
runtime governed by its own mirror contract. Devin adaptations listed in
``skills-mirror-contract.json`` are preserved: existing variant files are never
overwritten automatically, while required-identical files are synchronized.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai import sync_ai_governance


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _devin_drift(root: Path) -> tuple[list[dict[str, str]], dict[str, object]]:
    contract = sync_ai_governance._load_skills_mirror_contract(root)
    paths = sync_ai_governance._contract_paths(root, contract)
    canonical = paths["canonical"]
    devin = paths["devin"]
    optional, variants, identical = sync_ai_governance._codex_devin_parity_rules(
        contract
    )
    source_files = sync_ai_governance._relative_files(canonical)
    target_files = sync_ai_governance._relative_files(devin)
    entries: list[dict[str, str]] = []
    for relative in sorted(source_files - target_files):
        if not _matches(relative, optional):
            entries.append({"runtime": "devin", "change": "added", "path": relative})
    for relative in sorted(target_files - source_files):
        if not _matches(relative, optional):
            entries.append(
                {"runtime": "devin", "change": "unexpected", "path": relative}
            )
    for relative in sorted(source_files & target_files):
        if (canonical / relative).read_bytes() == (devin / relative).read_bytes():
            continue
        if _matches(relative, identical) or not _matches(relative, variants):
            entries.append({"runtime": "devin", "change": "modified", "path": relative})
    return entries, contract


def _sync_devin(root: Path, contract: dict[str, object]) -> list[str]:
    paths = sync_ai_governance._contract_paths(root, contract)
    canonical = paths["canonical"]
    devin = paths["devin"]
    optional, variants, identical = sync_ai_governance._codex_devin_parity_rules(
        contract
    )
    source_files = sync_ai_governance._relative_files(canonical)
    target_files = sync_ai_governance._relative_files(devin)
    synchronized: list[str] = []
    for relative in sorted(source_files):
        source = canonical / relative
        target = devin / relative
        missing_required = relative not in target_files and not _matches(
            relative, optional
        )
        required_update = (
            relative in target_files
            and source.read_bytes() != target.read_bytes()
            and (_matches(relative, identical) or not _matches(relative, variants))
        )
        if missing_required or required_update:
            _atomic_copy(source, target)
            synchronized.append(relative)
    return synchronized


def _run_junie(root: Path, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/ai/junie/check_junie_mirror.sh", mode],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--mode", choices=("check", "sync"), default="check")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.mode == "sync" and not args.approved:
        parser.error("--mode sync requires explicit --approved")

    before, contract = _devin_drift(root)
    synced: list[str] = []
    junie_mode = "--check"
    if args.mode == "sync":
        junie_mode = "--sync"
        synced = _sync_devin(root, contract)
        sync_ai_governance.sync_skill_mirrors(root, check_only=False)
    junie = _run_junie(root, junie_mode)
    after, _ = _devin_drift(root)
    validation = sync_ai_governance._validate_codex_devin_parity(
        sync_ai_governance._contract_paths(root, contract), contract
    )
    payload: dict[str, object] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "approved": args.approved,
        "drift_before": before,
        "synchronized_devin_paths": synced,
        "drift_after": after,
        "junie": {
            "returncode": junie.returncode,
            "stdout": junie.stdout.strip(),
            "stderr": junie.stderr.strip(),
        },
        "devin_validation_issues": validation,
    }
    _write_report(args.report, payload)
    ok = junie.returncode == 0 and not validation and not after
    print(f"Runtime skill sync report: {args.report}")
    if not ok:
        print("Runtime skill parity FAILED", file=sys.stderr)
        return 1
    print("Runtime skill parity OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
