#!/usr/bin/env python3
"""Summarize reports/basedpyright.json diagnostics."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPORT = Path("reports/basedpyright.json")


def norm(path: str) -> str:
    return path.replace("\\", "/")


def main() -> None:
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    diags = data["generalDiagnostics"]
    print("summary", data["summary"])
    print("total", len(diags))
    print("severity", Counter(d.get("severity") for d in diags))

    pkg: Counter[str] = Counter()
    for d in diags:
        f = norm(d.get("file", ""))
        if "/src/memory/" in f:
            pkg["memory"] += 1
        elif "/src/bioetl/" in f:
            pkg["bioetl"] += 1
        else:
            pkg["other"] += 1
    print("by pkg", pkg)

    noise = {
        "reportUninitializedInstanceVariable",
        "reportImportCycles",
        "reportMissingSuperCall",
    }
    bioetl = [d for d in diags if "/src/bioetl/" in norm(d.get("file", ""))]
    bioetl_real = [d for d in bioetl if d.get("rule") not in noise]
    print("bioetl total", len(bioetl), "without noise", len(bioetl_real))
    print("rules", Counter(d.get("rule") for d in bioetl_real).most_common(20))

    files: Counter[str] = Counter()
    for d in bioetl_real:
        files[norm(d["file"]).split("/src/")[-1]] += 1
    print("top bioetl files without noise:")
    for f, n in files.most_common(25):
        print(n, f)

    print("\n=== reportUndefinedVariable ===")
    for d in bioetl_real:
        if d.get("rule") == "reportUndefinedVariable":
            f = norm(d["file"]).split("/src/")[-1]
            line = d["range"]["start"]["line"] + 1
            print(f"{f}:{line}: {d['message'][:180]}")

    print("\n=== reportAttributeAccessIssue sample ===")
    count = 0
    for d in bioetl_real:
        if d.get("rule") != "reportAttributeAccessIssue":
            continue
        f = norm(d["file"]).split("/src/")[-1]
        line = d["range"]["start"]["line"] + 1
        print(f"{f}:{line}: {d['message'][:180]}")
        count += 1
        if count >= 20:
            break

    print("\n=== reportArgumentType sample ===")
    count = 0
    for d in bioetl_real:
        if d.get("rule") != "reportArgumentType":
            continue
        f = norm(d["file"]).split("/src/")[-1]
        line = d["range"]["start"]["line"] + 1
        print(f"{f}:{line}: {d['message'][:180]}")
        count += 1
        if count >= 20:
            break


if __name__ == "__main__":
    main()
