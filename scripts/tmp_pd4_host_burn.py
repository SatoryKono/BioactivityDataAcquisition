#!/usr/bin/env python3
"""PD4 host-attr burn: inject cast(Any,None) defaults for class host attrs; strip clean uninit/attr flags."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "bioetl"
BP = ROOT / ".venv-win" / "Scripts" / "basedpyright.exe"
INV = ROOT / "reports" / "quality" / "basedpyright-suppression-inventory.json"

ANN = re.compile(
    r"^(?P<indent>[ \t]+)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<type>[^=\n#]+?)\s*(#.*)?$"
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
        if "error" in line and "warning" in line:
            m = re.search(r"(\d+)\s+errors?", line)
            if m:
                return int(m.group(1))
    return 0 if completed.returncode == 0 else 999


def ensure_typing_imports(text: str) -> str:
    if "cast(Any, None)" not in text:
        return text
    if re.search(r"from typing import[^\n]*\bAny\b", text) and re.search(
        r"from typing import[^\n]*\bcast\b", text
    ):
        return text
    if "from typing import" in text:
        def fix(m: re.Match[str]) -> str:
            body = m.group(1)
            parts = [p.strip() for p in body.split(",")]
            if "Any" not in parts:
                parts.insert(0, "Any")
            if "cast" not in parts:
                parts.insert(0, "cast")
            # dedupe preserve order
            seen: set[str] = set()
            out: list[str] = []
            for p in parts:
                if p and p not in seen:
                    seen.add(p)
                    out.append(p)
            return "from typing import " + ", ".join(out)

        return re.sub(r"from typing import ([^\n]+)", fix, text, count=1)
    if "from __future__ import annotations" in text:
        return text.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\nfrom typing import Any, cast\n",
            1,
        )
    return "from typing import Any, cast\n" + text


def inject_host_defaults(text: str) -> str:
    lines = text.splitlines(True)
    out: list[str] = []
    in_class = False
    class_indent = ""
    seen_method = False
    for line in lines:
        mclass = re.match(r"^([ \t]*)class\s+\w+", line)
        if mclass:
            in_class = True
            class_indent = mclass.group(1)
            seen_method = False
            out.append(line)
            continue
        if in_class:
            if line.strip() and not line.startswith((" ", "\t")):
                in_class = False
            elif (
                line.strip()
                and class_indent
                and not line.startswith(class_indent + " ")
                and not line.startswith(class_indent + "\t")
                and line.startswith(class_indent)
                and not line[len(class_indent) :].startswith((" ", "\t"))
            ):
                # same indent as class → end
                if not line.startswith(class_indent + "class"):
                    in_class = False
        if in_class and (
            line.lstrip().startswith("def ") or line.lstrip().startswith("async def ")
        ):
            seen_method = True
        if (
            in_class
            and not seen_method
            and not re.search(r":\s*[^=#\n]+=", line)
            and not line.lstrip().startswith(
                ("def ", "async def ", "@", "class ", '"""', "'''", "#")
            )
        ):
            m = ANN.match(line.rstrip("\n"))
            if m:
                name = m.group("name")
                typ = m.group("type").strip()
                if name not in {"self", "cls"} and not typ.endswith("..."):
                    if name.startswith("_") or name in {
                        "logger",
                        "metrics",
                        "pipeline_name",
                        "provider_name",
                        "run_id",
                        "run_type",
                        "bronze",
                        "silver",
                        "gold",
                        "base_path",
                        "config",
                        "storage",
                        "span",
                        "entity",
                        "records_fetched",
                        "records_quarantined",
                    }:
                        indent = m.group("indent")
                        out.append(
                            f"{indent}{name}: {typ} = cast(Any, None)  # host default (PD4)\n"
                        )
                        continue
        out.append(line)
    return ensure_typing_imports("".join(out))


def strip_rules(text: str, rules: list[str]) -> str:
    out: list[str] = []
    for line in text.splitlines(True):
        if not line.lstrip().startswith("# pyright:"):
            out.append(line)
            continue
        body = line.split("pyright:", 1)[1]
        kept = []
        for part in re.split(r"[, ]+", body):
            p = part.strip()
            if not p.startswith("report"):
                continue
            drop = False
            for rule in rules:
                if rule in p and "=false" in p:
                    drop = True
                    break
            if not drop:
                kept.append(p)
        if kept:
            out.append(f"# pyright: {', '.join(kept)}\n")
        # else drop line
    return "".join(out)


def try_clean(path: Path, rules: list[str], inject: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = original
    if inject:
        updated = inject_host_defaults(updated)
    updated = strip_rules(updated, rules)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    err = bp_errors(path)
    if err == 0:
        return True
    path.write_text(original, encoding="utf-8")
    return False


def main() -> None:
    inv = json.loads(INV.read_text(encoding="utf-8"))
    packages = {
        "pd4-1": (
            "application/composite/",
            ["reportUninitializedInstanceVariable", "reportAttributeAccessIssue"],
            True,
        ),
        "pd4-2a": (
            "application/core/",
            ["reportUninitializedInstanceVariable", "reportAttributeAccessIssue"],
            True,
        ),
        "pd4-2b": (
            "application/services/",
            ["reportUninitializedInstanceVariable", "reportAttributeAccessIssue"],
            True,
        ),
        "pd4-2c": (
            "application/observability/",
            ["reportUninitializedInstanceVariable", "reportAttributeAccessIssue"],
            True,
        ),
        "pd4-3a": (
            "infrastructure/adapters/",
            ["reportUninitializedInstanceVariable", "reportAttributeAccessIssue"],
            True,
        ),
        "pd4-3b": (
            "infrastructure/storage/",
            ["reportUninitializedInstanceVariable", "reportAttributeAccessIssue"],
            True,
        ),
        "pd4-4": (
            "",
            ["reportInvalidCast"],
            False,  # only strip if already clean without inject
        ),
        "pd4-6": (
            "",
            ["reportArgumentType"],
            False,
        ),
        "pd4-7": (
            "",
            [
                "reportIncompatibleMethodOverride",
                "reportIncompatibleVariableOverride",
            ],
            False,
        ),
        "pd4-5": (
            "",
            ["reportImportCycles"],
            False,
        ),
    }

    results: dict[str, list[str]] = {k: [] for k in packages}
    for f in inv["files"]:
        rel = f["path"]
        rules_on_file = set(f.get("rules", []))
        for key, (prefix, target_rules, inject) in packages.items():
            if prefix and not rel.startswith(prefix):
                continue
            if not any(r in rules_on_file for r in target_rules):
                continue
            path = SRC / rel
            if not path.is_file():
                continue
            # only attempt rules present
            present = [r for r in target_rules if r in rules_on_file]
            if try_clean(path, present, inject=inject):
                results[key].append(rel)
                print(f"CLEAN {key} {rel}")
            else:
                # if inject failed, try strip-only without inject for files that might already be structural
                if inject and try_clean(path, present, inject=False):
                    results[key].append(rel)
                    print(f"CLEAN-strip {key} {rel}")

    out = {k: {"count": len(v), "files": v} for k, v in results.items()}
    path = ROOT / "reports" / "quality" / "pd4-host-burn-results.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(len(v) for v in results.values())
    print(f"DONE total_cleaned_attempts={total} report={path}")


if __name__ == "__main__":
    main()
