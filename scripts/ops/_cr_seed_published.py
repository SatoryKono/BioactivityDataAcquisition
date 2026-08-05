#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path

out = subprocess.check_output(
    [
        "gh",
        "issue",
        "list",
        "--repo",
        "SatoryKono/BioactivityDataAcquisition",
        "--state",
        "open",
        "--limit",
        "100",
        "--search",
        "CR-FULL Wave A in:title",
        "--json",
        "number,title,url",
    ],
    text=True,
)
issues = json.loads(out)
keys: list[str] = []
urls: list[str] = []
for it in issues:
    m = re.search(r"residual in `([^`]+)`", it["title"])
    if m:
        keys.append(m.group(1))
        urls.append(it["url"])
        print(it["number"], m.group(1))
path = Path("/mnt/c/Users/Fedor/bioetl-cr-artifacts/20260805/PUBLISHED_wave_A.json")
path.write_text(
    json.dumps({"path_keys": sorted(set(keys)), "urls": urls}, indent=2),
    encoding="utf-8",
)
print("seeded", len(keys), "keys ->", path)
