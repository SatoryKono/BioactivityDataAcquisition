"""Refresh a source-only projection without rewriting historical topology evidence.

This is not the producer of the historical evidence pack. It only projects the
verified module inventory into a separately delimited current-source binding.
No measurement identity, coverage, audit date or acceptance status is generated.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.engineering.qa.report_module_coverage_inventory import (
    compute_source_tree_sha256,
)

ROOT = Path(__file__).resolve().parents[3]
INVENTORY = Path("reports/quality/module-coverage-inventory.json")
SUMMARY = Path("docs/reports/evidence/project-package-topology/SUMMARY.md")
START = "<!-- current-source-binding:start -->"
END = "<!-- current-source-binding:end -->"
BOOTSTRAP_PROFILE = Path("reports/quality/test-bootstrap-fixture-scope-profile.json")


def _measured_bootstrap_file_count(root: Path, reference: str) -> int:
    """Count profiled modules from the original JUnit, preserving capture identity."""
    from scripts.engineering.common.repo_paths import resolve_output_path

    path = resolve_output_path(reference, root=root)
    modules = set()
    for case in ET.parse(path).iter("testcase"):
        parts = case.attrib["classname"].split(".")
        if parts[:4] != ["tests", "unit", "composition", "bootstrap"]:
            raise ValueError("Foreign test in bootstrap profile JUnit")
        index = next(i for i, part in enumerate(parts) if part.startswith("test_"))
        modules.add(".".join(parts[: index + 1]))
    if not modules:
        raise ValueError("Empty bootstrap profile JUnit")
    return len(modules)


def bind_bootstrap_profile(
    root: Path, digest: str, test_digest: str, *, update: bool
) -> bool:
    """Add a live topology view without relabeling the historical timing profile."""
    path = root / BOOTSTRAP_PROFILE
    profile = json.loads(path.read_text(encoding="utf-8"))
    measured_count = _measured_bootstrap_file_count(
        root, profile["measurement_provenance"]["junit"]
    )
    if profile["result"]["test_file_count"] != measured_count:
        raise ValueError("Bootstrap profile file count differs from its measured JUnit")
    files = sorted(
        p.relative_to(root).as_posix()
        for p in (root / "tests/unit/composition/bootstrap").rglob("test_*.py")
    )
    binding = {
        "kind": "source_topology_only",
        "source_tree_sha256": digest,
        "test_governance_source_tree_sha256": test_digest,
        "test_file_count": len(files),
        "test_files": files,
        "measured_test_file_count": measured_count,
    }
    current = profile.get("current_source_binding") == binding
    if update and not current:
        profile["current_source_binding"] = binding
        path.write_text(
            json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return current


def render_binding(
    text: str,
    digest: str,
    count: int,
    statuses: dict[str, int] | None = None,
    assertless: int | None = None,
) -> str:
    """Keep historical bytes intact and replace only this producer's projection."""
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or count < 0:
        raise ValueError("Invalid source inventory identity")
    if text.count(START) != text.count(END) or text.count(START) > 1:
        raise ValueError("Ambiguous source binding delimiters")
    classifications = ""
    if statuses is not None:
        classifications = (
            f"- `{statuses['fully_covered']}` fully covered\n"
            f"- `{statuses['partially_covered']}` partially covered\n"
        )
    if assertless is not None:
        classifications += (
            f"- Test inventory: `assertless_total_candidates={assertless}`\n"
        )
    block = (
        f"{START}\n\n## Current source inventory binding\n\n"
        f"- `source_tree_sha256={digest}`\n"
        f"- `source_module_count={count}`\n"
        f"- Source modules: `{count}`\n"
        f"{classifications}\n"
        "Derived by scripts/engineering/qa/report_topology_source_binding.py from\n"
        "the verified module inventory. This is a source-only projection, not a\n"
        "new coverage measurement or a complete topology re-audit. Historical raw\n"
        f"evidence and capture identity above remain unchanged.\n\n{END}"
    )
    if START not in text:
        return text + ("\n" if text.endswith("\n") else "\n\n") + block + "\n"
    start = text.index(START)
    end = text.index(END, start) + len(END)
    return text[:start] + block + text[end:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    payload = json.loads((root / INVENTORY).read_text(encoding="utf-8"))
    digest = compute_source_tree_sha256(repo_root=root)
    count = len(payload["modules"])
    if (
        payload["source_tree_sha256"] != digest
        or payload["summary"]["source_module_count"] != count
    ):
        raise ValueError("Module inventory is stale; regenerate it before binding")
    governance = json.loads(
        (root / "reports/quality/test-governance-current.json").read_text(
            encoding="utf-8"
        )
    )
    from scripts.engineering.qa.report_test_governance_audit import (
        _compute_test_governance_source_tree_sha256,
    )

    if governance["source_tree_sha256"] != _compute_test_governance_source_tree_sha256(
        str(root)
    ):
        raise ValueError("Test inventory is stale; regenerate it before binding")
    current = bind_bootstrap_profile(
        root, digest, governance["source_tree_sha256"], update=args.update
    )
    for target in (SUMMARY, Path("docs/02-architecture/current-state-inventory.md")):
        path = root / target
        existing = path.read_text(encoding="utf-8")
        expected = render_binding(
            existing,
            digest,
            count,
            payload["summary"]["status_counts"],
            governance["report"]["assertless_total_candidates"],
        )
        current = current and existing == expected
        if args.update:
            path.write_text(expected, encoding="utf-8")
    return 0 if args.update or current else 1


if __name__ == "__main__":
    raise SystemExit(main())
