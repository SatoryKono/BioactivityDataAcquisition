#!/usr/bin/env python3
"""Generate or check `.agents/skills` adapters for canonical Codex skills."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from native_runtime_contract import (
    DISCOVERY_SKILLS_DIR,
    GENERATED_MARKER,
    REPO_ROOT,
    canonical_skills,
    render_skill_adapter,
    validate_skill_adapters,
)


def sync(repo_root: Path) -> None:
    skills = canonical_skills(repo_root)
    discovery_root = repo_root / DISCOVERY_SKILLS_DIR
    discovery_root.mkdir(parents=True, exist_ok=True)

    for stale_file in sorted(discovery_root.glob("*/SKILL.md")):
        if stale_file.parent.name in skills:
            continue
        if GENERATED_MARKER in stale_file.read_text(encoding="utf-8"):
            shutil.rmtree(stale_file.parent)

    for directory_name, (_, description) in skills.items():
        destination = discovery_root / directory_name / "SKILL.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            render_skill_adapter(directory_name, description), encoding="utf-8"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail on discovery drift")
    mode.add_argument("--sync", action="store_true", help="refresh generated adapters")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    if args.sync:
        sync(repo_root)

    findings = validate_skill_adapters(repo_root)
    if findings:
        for finding in findings:
            print(f"[FAIL] {finding.code}: {finding.message} ({finding.path})")
        return 1
    print(f"[OK] {len(canonical_skills(repo_root))} native skill adapters are in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
