#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

root = Path.home() / ".coderabbit" / "reviews"
print("root", root, "exists", root.exists())

newest = sorted(root.rglob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
print("json files", len(newest))
for p in newest[:25]:
    if p.name in {
        "diff.json",
        "git.json",
        "internalState.json",
        "incrementalDiff.json",
    }:
        continue
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        print("ERR", p, exc)
        continue
    if isinstance(data, dict):
        keys = list(data.keys())[:20]
        print(f"{p.relative_to(root)} dict keys={keys}")
        # dump nested type hints
        for k, v in list(data.items())[:8]:
            if isinstance(v, list):
                print(f"  {k}: list[{len(v)}]", type(v[0]).__name__ if v else "")
                if v and isinstance(v[0], dict):
                    print("   item_keys", list(v[0].keys())[:15])
            elif isinstance(v, dict):
                print(f"  {k}: dict keys={list(v.keys())[:12]}")
            else:
                print(f"  {k}: {type(v).__name__}")
    elif isinstance(data, list):
        print(f"{p.relative_to(root)} list[{len(data)}]")
        if data and isinstance(data[0], dict):
            print("  item_keys", list(data[0].keys())[:15])
