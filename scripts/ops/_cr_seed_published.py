#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", default="SatoryKono/BioactivityDataAcquisition")
    parser.add_argument("--search", default="CR-FULL Wave A in:title")
    args = parser.parse_args()
    out = subprocess.check_output(
        [
            "gh", "issue", "list", "--repo", args.repo, "--state", "open",
            "--limit", "100", "--search", args.search,
            "--json", "number,title,url",
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"path_keys": sorted(set(keys)), "urls": urls}, indent=2),
        encoding="utf-8",
    )
    print("seeded", len(keys), "keys ->", args.output)


if __name__ == "__main__":
    main()
