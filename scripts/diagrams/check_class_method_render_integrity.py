#!/usr/bin/env python3
"""Check that classDiagram methods are rendered correctly in SVG artifacts.

Validations:
1. Method names declared in class-diagram `.mmd` files exist in rendered SVG.
2. Method labels in SVG are not split across lines inside identifiers.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlunsplit

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from .diagram_paths import source_dir as diagram_source_dir
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import source_dir as diagram_source_dir

SVG_NS = urlunsplit(("http", "www.w3.org", "/2000/svg", "", ""))
NS = {"svg": SVG_NS}

CLASS_DECL_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)\s*\{\s*$")
METHOD_DECL_RE = re.compile(r"^\s*[+\-#~]\s*([A-Za-z_\\][\\w]*)\s*\(")


@dataclass
class IntegrityIssue:
    file: str
    severity: str
    rule: str
    message: str


def _normalize_whitespace(raw: str) -> str:
    return " ".join(raw.split()).strip()


def _strip_class_id_suffix(raw_class_id: str) -> str:
    """Convert Mermaid node id `classId-Name-3` to class name `Name`."""
    if not raw_class_id.startswith("classId-"):
        return raw_class_id
    candidate = raw_class_id[len("classId-") :]
    if "-" not in candidate:
        return candidate
    maybe_name, maybe_idx = candidate.rsplit("-", 1)
    if maybe_idx.isdigit():
        return maybe_name
    return candidate


def _resolve_methods_group_class_name(
    methods_group: ET.Element,
    parent_map: dict[ET.Element, ET.Element],
) -> str:
    ancestor = methods_group
    while ancestor is not None:
        raw_id = ancestor.attrib.get("id", "")
        if raw_id.startswith("classId-"):
            return _strip_class_id_suffix(raw_id)
        ancestor = parent_map.get(ancestor)
    return ""


def _collect_methods_group_text(methods_group: ET.Element) -> list[str]:
    method_text_parts = [
        text
        for tspan in methods_group.findall(".//svg:tspan", NS)
        if (text := _normalize_whitespace(tspan.text or ""))
    ]
    if method_text_parts:
        return method_text_parts

    # Fallback when only foreignObject is present.
    return [
        text
        for foreign_object in methods_group.findall(".//svg:foreignObject", NS)
        if (text := _normalize_whitespace(" ".join(foreign_object.itertext())))
    ]


def _collect_split_method_issues(
    methods_group: ET.Element,
    class_name: str,
) -> list[tuple[str, str, str]]:
    split_issues: list[tuple[str, str, str]] = []
    for label in methods_group.findall('./svg:g[@class="label"]', NS):
        spans = [
            text
            for tspan in label.findall(".//svg:tspan", NS)
            if (text := _normalize_whitespace(tspan.text or ""))
        ]
        for left, right in itertools.pairwise(spans):
            # Broken split example: "start_execution_sp" + "an()"
            if re.search(r"\w$", left) and re.match(r"^\w", right):
                split_issues.append((class_name, left, right))
    return split_issues


def parse_expected_methods(mmd_path: Path) -> dict[str, list[str]]:
    lines = mmd_path.read_text(encoding="utf-8").splitlines()
    in_class: str | None = None
    methods: dict[str, list[str]] = {}

    for line in lines:
        class_match = CLASS_DECL_RE.match(line)
        if class_match:
            in_class = class_match.group(1)
            methods.setdefault(in_class, [])
            continue

        if in_class is not None and line.strip() == "}":
            in_class = None
            continue

        if in_class is None:
            continue

        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue

        method_match = METHOD_DECL_RE.match(stripped)
        if not method_match:
            continue
        method_name = method_match.group(1).replace("\\_", "_")
        methods[in_class].append(method_name)

    return methods


def parse_svg_methods(
    svg_path: Path,
) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    parent_map = {child: parent for parent in root.iter() for child in parent}

    rendered_by_class: dict[str, str] = {}
    split_issues: list[tuple[str, str, str]] = []

    for methods_group in root.findall('.//svg:g[@class="methods-group text"]', NS):
        class_name = _resolve_methods_group_class_name(methods_group, parent_map)
        if not class_name:
            continue

        method_text_parts = _collect_methods_group_text(methods_group)
        rendered_by_class[class_name] = " ".join(method_text_parts)

        split_issues.extend(_collect_split_method_issues(methods_group, class_name))

    return rendered_by_class, split_issues


def check_pair(mmd_path: Path, svg_path: Path) -> list[IntegrityIssue]:
    issues: list[IntegrityIssue] = []
    file_name = str(mmd_path)

    if not svg_path.exists():
        return [
            IntegrityIssue(
                file=file_name,
                severity="ERROR",
                rule="METHOD-001",
                message=f"Rendered SVG not found: {svg_path}",
            )
        ]

    expected = parse_expected_methods(mmd_path)
    rendered_by_class, split_issues = parse_svg_methods(svg_path)

    for class_name, expected_methods in expected.items():
        if not expected_methods:
            continue
        rendered = rendered_by_class.get(class_name, "")
        if not rendered:
            issues.append(
                IntegrityIssue(
                    file=file_name,
                    severity="ERROR",
                    rule="METHOD-001",
                    message=f"Missing methods block in SVG for class '{class_name}'",
                )
            )
            continue
        for method_name in expected_methods:
            if method_name not in rendered:
                issues.append(
                    IntegrityIssue(
                        file=file_name,
                        severity="ERROR",
                        rule="METHOD-001",
                        message=(
                            "Method name missing or altered in SVG for class "
                            f"'{class_name}': {method_name}"
                        ),
                    )
                )

    for class_name, left, right in split_issues:
        issues.append(
            IntegrityIssue(
                file=file_name,
                severity="ERROR",
                rule="METHOD-002",
                message=(
                    f"Method identifier split across lines in class '{class_name}': "
                    f"'{left}' + '{right}'"
                ),
            )
        )

    return issues


def resolve_sources(source_dir: Path, explicit_files: list[Path]) -> list[Path]:
    if explicit_files:
        resolved: list[Path] = []
        for path in explicit_files:
            resolved.append(path if path.is_absolute() else Path.cwd() / path)
        return sorted(resolved)

    return sorted(source_dir.glob("*.mmd"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify class-diagram method integrity between .mmd and rendered SVG files.",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=diagram_source_dir("class-diagrams"),
        help="Directory containing class-diagram .mmd sources.",
    )
    parser.add_argument(
        "--svg-dir",
        type=Path,
        default=None,
        help="Directory containing rendered .svg files (default: <source-dir>/svg).",
    )
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Specific .mmd file to check (repeatable).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print issues as JSON.",
    )
    args = parser.parse_args()

    source_root = (
        args.source_dir
        if args.source_dir.is_absolute()
        else Path.cwd() / args.source_dir
    )
    svg_dir_input = args.svg_dir if args.svg_dir is not None else source_root / "svg"
    svg_dir = (
        svg_dir_input if svg_dir_input.is_absolute() else Path.cwd() / svg_dir_input
    )

    explicit_files = [Path(raw) for raw in args.file]
    sources = resolve_sources(source_root, explicit_files)
    if not sources:
        sys.stderr.write(f"No class-diagram sources found in {source_root}\n")
        return 2

    all_issues: list[IntegrityIssue] = []
    for mmd_path in sources:
        if mmd_path.suffix != ".mmd":
            continue
        svg_path = svg_dir / f"{mmd_path.stem}.svg"
        all_issues.extend(check_pair(mmd_path, svg_path))

    if args.json_output:
        payload = {
            "files_checked": len(sources),
            "issues": [
                {
                    "file": issue.file,
                    "severity": issue.severity,
                    "rule": issue.rule,
                    "message": issue.message,
                }
                for issue in all_issues
            ],
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        if not all_issues:
            sys.stdout.write(
                f"class-method-render-integrity: OK ({len(sources)} files checked)\n"
            )
        else:
            for issue in all_issues:
                sys.stdout.write(
                    f"[{issue.severity}] {issue.rule} {issue.file}: {issue.message}\n"
                )
            sys.stdout.write(
                f"class-method-render-integrity: FAILED ({len(all_issues)} issues)\n"
            )

    return 1 if all_issues else 0


if __name__ == "__main__":
    sys.exit(main())
