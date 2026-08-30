#!/usr/bin/env python3
"""Diff helper for P1 (#9808) — generated file diff + catalog git diff.

CLI:
  python -m scripts.ai.prompts.diff --domain docs --profile audit-readonly
  python -m scripts.ai.prompts.diff --domain docs --profile audit-readonly --compare full-write
  python -m scripts.ai.prompts.diff --catalog
"""
from __future__ import annotations
import argparse, difflib, subprocess, sys
from pathlib import Path
try:
    from scripts.ai.prompts.registry import PROMPTS_ROOT as _RP, REPO_ROOT as _RR
    PROMPTS_ROOT, REPO_ROOT = _RP, _RR
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    PROMPTS_ROOT = REPO_ROOT / "docs/00-project/ai/prompts"
GENERATED_ROOT = PROMPTS_ROOT / "generated"
def _read(d: str, p: str) -> str:
    f = GENERATED_ROOT / d / f"{p}.md"
    if not f.is_file():
        raise FileNotFoundError(f"generated file not found: {f}")
    return f.read_text(encoding="utf-8").replace("\r\n", "\n")
def diff_domain(d: str, p: str, c: str | None, n: int) -> int:
    a = _read(d, p)
    if c is None:
        sys.stdout.write(a)
        return 0
    b = _read(d, c)
    diff = difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                                fromfile=f"{d}/{p}.md", tofile=f"{d}/{c}.md", n=n)
    out = "".join(diff)
    if not out:
        print(f"no diff: {d}/{p}.md == {d}/{c}.md")
        return 0
    sys.stdout.write(out)
    return 0
def diff_catalog(n: int) -> int:
    cmd = ["git", "--no-pager", "diff", f"--unified={n}", "--", str(GENERATED_ROOT)]
    try:
        r = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        print("git not found", file=sys.stderr)
        return 1
    if r.stdout: sys.stdout.write(r.stdout)
    if r.stderr: sys.stderr.write(r.stderr)
    if not r.stdout and not r.stderr: print("catalog: no git diff for generated/")
    return r.returncode
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m scripts.ai.prompts.diff", description="Diff helper (P1 #9808)")
    p.add_argument("--domain", default=None, help="Overlay domain slug")
    p.add_argument("--profile", default=None, help="Profile name")
    p.add_argument("--compare", default=None, help="Second profile to diff against")
    p.add_argument("--catalog", action="store_true", help="Show git diff for generated/")
    p.add_argument("--unified", type=int, default=3, help="Unified context lines")
    return p
def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if a.catalog: return diff_catalog(a.unified)
    if a.domain and a.profile:
        try: return diff_domain(a.domain, a.profile, a.compare, a.unified)
        except FileNotFoundError as e: print(str(e), file=sys.stderr); return 1
    build_parser().error("use --catalog or --domain <d> --profile <p> [--compare <p2>]")
    return 2
if __name__ == "__main__": raise SystemExit(main())
