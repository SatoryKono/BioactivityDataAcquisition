#!/usr/bin/env python3
"""Per-rule suppression strip trial; keep removal only if basedpyright file is clean."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "bioetl"
BP = ROOT / ".venv-win" / "Scripts" / "basedpyright.exe"
INV = ROOT / "reports" / "quality" / "basedpyright-suppression-inventory.json"

RULE_LINE = re.compile(
    r"^(?P<prefix>\s*#\s*pyright:\s*)(?P<body>.+?)(?P<suffix>\s*)$"
)


def bp_errors(path: Path) -> int:
    try:
        completed = subprocess.run(
            [str(BP), str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 999
    text = (completed.stdout or "") + "\n" + (completed.stderr or "")
    for line in reversed(text.splitlines()):
        line = line.strip()
        if "error" in line and "warning" in line:
            m = re.search(r"(\d+)\s+errors?", line)
            if m:
                return int(m.group(1))
    return 0 if completed.returncode == 0 else 999


def remove_rule_from_text(text: str, rule: str) -> str:
    """Remove one reportX=false from pyright directive lines; drop empty directives."""
    out_lines: list[str] = []
    target = f"{rule}=false"
    for line in text.splitlines(True):
        m = RULE_LINE.match(line.rstrip("\n"))
        if not m or target not in m.group("body"):
            out_lines.append(line)
            continue
        body = m.group("body")
        # split on commas/spaces
        parts = [p.strip() for p in re.split(r"[, ]+", body) if p.strip()]
        parts = [p for p in parts if p != target and not p.endswith(f"{rule}=false")]
        # also filter exact
        parts = [p for p in parts if rule not in p or "=false" not in p]
        if not parts:
            # drop entire directive line
            continue
        newline = f"{m.group('prefix')}{', '.join(parts)}\n"
        if line.endswith("\r\n"):
            newline = newline.replace("\n", "\r\n")
        out_lines.append(newline)
    return "".join(out_lines)


def main() -> None:
    inv = json.loads(INV.read_text(encoding="utf-8"))
    # Prefer high-count rules first
    rule_order = [
        "reportIncompatibleVariableOverride",
        "reportIncompatibleMethodOverride",
        "reportConstantRedefinition",
        "reportImportCycles",
        "reportUninitializedInstanceVariable",
        "reportAttributeAccessIssue",
        "reportInvalidCast",
        "reportArgumentType",
        "reportCallIssue",
        "reportPossiblyUnboundVariable",
        "reportOptionalMemberAccess",
        "reportMissingSuperCall",
        "reportUnsafeMultipleInheritance",
        "reportFunctionMemberAccess",
        "reportGeneralTypeIssues",
        "reportReturnType",
        "reportImplicitAbstractClass",
        "reportTypedDictNotRequiredAccess",
        "reportInconsistentOverload",
    ]

    removed_rules: list[dict[str, str]] = []
    attempts = 0

    for rule in rule_order:
        files = [
            f["path"]
            for f in inv["files"]
            if rule in f.get("rules", [])
        ]
        print(f"\n=== rule {rule} candidates={len(files)} ===")
        for rel in files:
            path = SRC / rel
            if not path.is_file():
                continue
            original = path.read_text(encoding="utf-8")
            if f"{rule}=false" not in original:
                continue
            updated = remove_rule_from_text(original, rule)
            if updated == original:
                continue
            path.write_text(updated, encoding="utf-8")
            attempts += 1
            err = bp_errors(path)
            if err == 0:
                removed_rules.append({"path": rel, "rule": rule})
                print(f"  REMOVED {rule} from {rel}")
            else:
                path.write_text(original, encoding="utf-8")
                print(f"  keep {rule} on {rel} (errors={err})")
            sys.stdout.flush()

    out = {
        "attempts": attempts,
        "removed_rule_assignments": len(removed_rules),
        "removed": removed_rules,
    }
    path = ROOT / "reports" / "quality" / "pd3-suppression-rule-strip.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nDONE attempts={attempts} removed_assignments={len(removed_rules)} -> {path}")


if __name__ == "__main__":
    main()
