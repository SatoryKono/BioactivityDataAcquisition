"""Parse a pytest junitxml file and print failure summaries."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"missing {path}")
        return 1
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    fails = errors = skips = tests = 0
    cases: list[tuple[str, str, str, str]] = []
    for suite in suites:
        tests += int(suite.attrib.get("tests", 0) or 0)
        fails += int(suite.attrib.get("failures", 0) or 0)
        errors += int(suite.attrib.get("errors", 0) or 0)
        skips += int(suite.attrib.get("skipped", 0) or 0)
        for case in suite.iter("testcase"):
            for child in list(case):
                if child.tag in {"failure", "error"}:
                    node = f"{case.attrib.get('classname', '')}::{case.attrib.get('name', '')}"
                    msg = child.attrib.get("message") or child.attrib.get("type") or ""
                    text = (child.text or "").replace("\n", " | ")
                    cases.append((child.tag, node, msg[:240], text[:500]))
                    break
    print(f"tests={tests} failures={fails} errors={errors} skipped={skips}")
    for kind, node, msg, text in cases:
        print("---")
        print(kind, node)
        print("MSG", msg)
        print("TXT", text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
