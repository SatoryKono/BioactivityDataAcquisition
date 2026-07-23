#!/usr/bin/env python3
"""Parse CodeRabbit agent NDJSON architecture review findings."""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def layer_of(working_directory: str | None) -> str:
    if not working_directory:
        return "?"
    path = working_directory.replace("\\", "/")
    mapping = (
        ("/src/bioetl/domain", "domain"),
        ("/src/bioetl/application", "application"),
        ("/src/bioetl/composition", "composition"),
        ("/src/bioetl/infrastructure", "infrastructure"),
        ("/src/bioetl/interfaces", "interfaces"),
        ("/tests/architecture", "tests/architecture"),
        ("/docs/02-architecture", "docs/02-architecture"),
    )
    for suffix, name in mapping:
        if path.endswith(suffix) or suffix in path:
            return name
    return path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: parse_cr_arch_findings.py <agent.ndjson>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    findings: list[dict[str, str]] = []
    completes: list[tuple[str, int]] = []
    current_dir: str | None = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = obj.get("type")
        if kind == "review_context":
            current_dir = obj.get("workingDirectory")
        elif kind == "finding":
            findings.append(
                {
                    "layer": layer_of(current_dir),
                    "severity": str(obj.get("severity") or "unknown"),
                    "file": str(obj.get("fileName") or "?"),
                    "text": str(obj.get("codegenInstructions") or ""),
                }
            )
        elif kind == "complete":
            completes.append((layer_of(current_dir), int(obj.get("findings") or 0)))
        elif kind == "error":
            print(
                "ERROR",
                layer_of(current_dir),
                obj.get("code") or obj.get("errorType"),
                str(obj.get("message") or "")[:200],
            )

    print(f"FILE={path}")
    print(f"TOTAL_FINDINGS={len(findings)}")
    print("BY_SEVERITY", dict(collections.Counter(f["severity"] for f in findings)))
    print("BY_LAYER", dict(collections.Counter(f["layer"] for f in findings)))
    print("COMPLETES", completes)
    print()
    for item in findings:
        text = " ".join(item["text"].split())
        # Drop boilerplate prefix when present
        for marker in (
            "Validate.\n\n",
            "validate.\n\n",
            "and validate.",
        ):
            if marker in item["text"]:
                text = " ".join(item["text"].split(marker, 1)[-1].split())
                break
        print(f"### [{item['severity'].upper()}] {item['layer']} :: {item['file']}")
        print(text[:600])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
