#!/usr/bin/env python3
"""Check or sync parity between `.codex/**` (source runtime) and `.junie/**` (mirror runtime).

Governance contract: `scripts/ai/junie/junie-mirror-contract.json`.

Modes:
  --check   Read-only validation. Exit 0 on parity, 1 on drift with a diff report.
  --sync    Copy missing/outdated files from `.codex/**` into `.junie/**`.
            Never writes into `.codex/**`. Preserves Junie runtime-only files
            (`.junie/agents/JUNIE-RUNTIME.md`, `.junie/guidelines.md`).

The two runtime trees are equal-peer canonical sources; `--sync` propagates
in one direction only (codex → junie). Bidirectional parity is a governance
contract, not an automated write policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPO_ROOT / "scripts" / "ai" / "junie" / "junie-mirror-contract.json"

type JsonObject = dict[str, Any]


def sha256_of(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at `path`.

    Line endings are normalized to LF so that Windows/POSIX checkouts
    produce identical hashes for text files. Binary files are hashed as-is
    (they will still match if identical bytes are on disk).
    """
    h = hashlib.sha256()
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    normalized = data.replace(b"\r\n", b"\n")
    h.update(normalized)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def load_contract() -> JsonObject:
    with CONTRACT_PATH.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"Junie mirror contract must be an object: {CONTRACT_PATH}")
    return cast(JsonObject, payload)


def collect_files(root: Path, exclude_prefixes: Iterable[str] = ()) -> dict[str, Path]:
    """Return {relative_path_from_root: absolute_path} for every regular file under `root`."""
    result: dict[str, Path] = {}
    if not root.exists():
        return result
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel_from_root = str(p.relative_to(root)).replace("\\", "/")
        if any(rel_from_root.startswith(prefix) for prefix in exclude_prefixes):
            continue
        result[rel_from_root] = p
    return result


def check_agents(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["agents"]
    codex_dir = REPO_ROOT / ".codex" / "agents"
    junie_dir = REPO_ROOT / ".junie" / "agents"
    exclude = set(scope.get("exclude_filenames", []))
    codex_files = {p.name for p in codex_dir.glob("py-*.md") if p.name not in exclude}
    junie_files = {p.name for p in junie_dir.glob("py-*.md")}
    missing_in_junie = sorted(codex_files - junie_files)
    extra_in_junie = sorted(junie_files - codex_files)
    for name in missing_in_junie:
        issues.append(f"[agents] missing in .junie/agents/: {name}")
    for name in extra_in_junie:
        issues.append(f"[agents] unexpected in .junie/agents/: {name}")
    for name in sorted(codex_files & junie_files):
        h_src = sha256_of(codex_dir / name)
        h_mir = sha256_of(junie_dir / name)
        if h_src != h_mir:
            issues.append(
                f"[agents] content drift: .junie/agents/{name} differs from .codex/agents/{name}"
            )


def check_shared_agent_docs(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["shared_agent_docs"]
    for src_rel, mir_rel in zip(
        scope["source_files"], scope["mirror_files"], strict=True
    ):
        src = REPO_ROOT / src_rel
        mir = REPO_ROOT / mir_rel
        if not mir.exists():
            issues.append(f"[shared_agent_docs] missing mirror: {mir_rel}")
            continue
        if not src.exists():
            issues.append(f"[shared_agent_docs] missing source: {src_rel}")
            continue
        if sha256_of(src) != sha256_of(mir):
            issues.append(f"[shared_agent_docs] content drift: {mir_rel} != {src_rel}")


def check_skills_catalog(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["skills_catalog"]
    src = REPO_ROOT / scope["source_file"]
    mir = REPO_ROOT / scope["mirror_file"]
    if not mir.exists():
        issues.append(f"[skills_catalog] missing mirror: {scope['mirror_file']}")
        return
    if not src.exists():
        issues.append(f"[skills_catalog] missing source: {scope['source_file']}")
        return
    if sha256_of(src) != sha256_of(mir):
        issues.append(
            f"[skills_catalog] content drift: {scope['mirror_file']} != {scope['source_file']}"
        )


def check_skills(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["skills"]
    exclude = set(scope.get("exclude_directory_names", []))
    codex_dir = REPO_ROOT / ".codex" / "skills"
    junie_dir = REPO_ROOT / ".junie" / "skills"
    codex_dirs = {
        p.name for p in codex_dir.iterdir() if p.is_dir() and p.name not in exclude
    }
    junie_dirs = {p.name for p in junie_dir.iterdir() if p.is_dir()}
    missing_in_junie = sorted(codex_dirs - junie_dirs)
    extra_in_junie = sorted(junie_dirs - codex_dirs)
    for name in missing_in_junie:
        issues.append(f"[skills] missing in .junie/skills/: {name}/")
    for name in extra_in_junie:
        issues.append(f"[skills] unexpected in .junie/skills/: {name}/")


def check_skill_contents(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["skill_contents"]
    exclude_prefixes = tuple(scope.get("exclude_relative_path_prefixes", []))
    codex_dir = REPO_ROOT / ".codex" / "skills"
    junie_dir = REPO_ROOT / ".junie" / "skills"
    codex_files = collect_files(codex_dir, exclude_prefixes)
    junie_files = collect_files(junie_dir, exclude_prefixes)
    # SKILLS-CATALOG.md is handled by check_skills_catalog(); skip here to avoid
    # duplicate reporting.
    codex_files.pop("SKILLS-CATALOG.md", None)
    junie_files.pop("SKILLS-CATALOG.md", None)
    missing_in_junie = sorted(set(codex_files) - set(junie_files))
    extra_in_junie = sorted(set(junie_files) - set(codex_files))
    for rel_path in missing_in_junie:
        issues.append(f"[skill_contents] missing in .junie/skills/: {rel_path}")
    for rel_path in extra_in_junie:
        issues.append(f"[skill_contents] unexpected in .junie/skills/: {rel_path}")
    for rel_path in sorted(set(codex_files) & set(junie_files)):
        h_src = sha256_of(codex_files[rel_path])
        h_mir = sha256_of(junie_files[rel_path])
        if h_src != h_mir:
            issues.append(f"[skill_contents] content drift: .junie/skills/{rel_path}")


def check_runtime_only_files(contract: JsonObject, issues: list[str]) -> None:
    ro = contract["runtime_only_files"]
    for path_str in ro["codex_only"]:
        if not (REPO_ROOT / path_str).exists():
            issues.append(f"[runtime_only] missing codex_only file: {path_str}")
    for path_str in ro["junie_only"]:
        if not (REPO_ROOT / path_str).exists():
            issues.append(f"[runtime_only] missing junie_only file: {path_str}")


def do_check(contract: JsonObject) -> int:
    issues: list[str] = []
    check_agents(contract, issues)
    check_shared_agent_docs(contract, issues)
    check_skills_catalog(contract, issues)
    check_skills(contract, issues)
    check_skill_contents(contract, issues)
    check_runtime_only_files(contract, issues)
    if issues:
        print("Junie mirror parity FAILED:", file=sys.stderr)
        for line in issues:
            print(f"  - {line}", file=sys.stderr)
        print(
            f"\nTotal drift entries: {len(issues)}.\n"
            "Run `bash scripts/ai/junie/check_junie_mirror.sh --sync` to sync .codex -> .junie.",
            file=sys.stderr,
        )
        return 1
    print(
        "Junie mirror parity OK: .codex/** == .junie/** (per junie-mirror-contract.json)."
    )
    return 0


def do_sync(contract: JsonObject) -> int:
    """One-way sync .codex → .junie for every file under parity scope.

    Never writes into `.codex/**`. Preserves Junie runtime-only files.
    """
    scope = contract["parity_scope"]
    # 1. Agents
    codex_agents = REPO_ROOT / ".codex" / "agents"
    junie_agents = REPO_ROOT / ".junie" / "agents"
    junie_agents.mkdir(parents=True, exist_ok=True)
    exclude_agents = set(scope["agents"].get("exclude_filenames", []))
    for src in codex_agents.glob("py-*.md"):
        if src.name in exclude_agents:
            continue
        dst = junie_agents / src.name
        shutil.copy2(src, dst)
    # Remove stray py-* files not in source
    codex_agent_names = {
        p.name for p in codex_agents.glob("py-*.md") if p.name not in exclude_agents
    }
    for stray in junie_agents.glob("py-*.md"):
        if stray.name not in codex_agent_names:
            stray.unlink()
    # 2. Shared agent docs
    for src_rel, mir_rel in zip(
        scope["shared_agent_docs"]["source_files"],
        scope["shared_agent_docs"]["mirror_files"],
        strict=True,
    ):
        src = REPO_ROOT / src_rel
        mir = REPO_ROOT / mir_rel
        mir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, mir)
    # 3. Skills catalog
    cat = scope["skills_catalog"]
    junie_skills = REPO_ROOT / ".junie" / "skills"
    junie_skills.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / cat["source_file"], REPO_ROOT / cat["mirror_file"])
    # 4. Skills directories (mirror the whole tree under .codex/skills/**)
    codex_skills = REPO_ROOT / ".codex" / "skills"
    exclude_skill_dirs = set(scope["skills"].get("exclude_directory_names", []))
    exclude_prefixes = tuple(
        scope["skill_contents"].get("exclude_relative_path_prefixes", [])
    )
    # Explicitly remove excluded skill directories from .junie side (they must
    # never exist as tracked mirror content, even if they pre-existed locally).
    for excluded in exclude_skill_dirs:
        stale_dir = junie_skills / excluded
        if stale_dir.exists():
            shutil.rmtree(stale_dir)
    codex_files = collect_files(codex_skills, exclude_prefixes)
    codex_files.pop("SKILLS-CATALOG.md", None)
    for rel_path, src in codex_files.items():
        # Skip files under excluded skill dirs
        top = rel_path.split("/", 1)[0]
        if top in exclude_skill_dirs:
            continue
        dst = junie_skills / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    # Remove stray files/dirs in junie skills that don't exist in codex
    junie_files = collect_files(junie_skills, exclude_prefixes)
    junie_files.pop("SKILLS-CATALOG.md", None)
    for rel_path in set(junie_files) - set(codex_files):
        top = rel_path.split("/", 1)[0]
        if top in exclude_skill_dirs:
            continue
        (junie_skills / rel_path).unlink()
    # Remove empty dirs
    for d in sorted(
        [p for p in junie_skills.rglob("*") if p.is_dir()],
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        try:
            d.rmdir()
        except OSError:
            pass
    print("Junie mirror sync complete (.codex -> .junie).")
    print("Re-running --check to validate final state...")
    return do_check(contract)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="read-only parity check")
    group.add_argument(
        "--sync", action="store_true", help="copy .codex/** into .junie/**"
    )
    args = parser.parse_args()
    contract = load_contract()
    if args.check:
        return do_check(contract)
    if args.sync:
        return do_sync(contract)
    return 2


if __name__ == "__main__":
    sys.exit(main())
