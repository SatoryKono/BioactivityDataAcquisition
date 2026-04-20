#!/usr/bin/env python3
"""Diagram regression quality gates for DIAG-T018..DIAG-T023.

This script implements policy-aligned checks from
`diagram-regression-test-plan.md` and emits a machine-readable JSON report
plus a markdown summary.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from .diagram_paths import (
        DIAGRAM_ROOT,
        QUALITY_GATE_MANIFEST,
        REPO_ROOT,
        source_dir,
    )
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import DIAGRAM_ROOT, QUALITY_GATE_MANIFEST, REPO_ROOT, source_dir


DEFAULT_TARGET = DIAGRAM_ROOT
DEFAULT_MANIFEST = QUALITY_GATE_MANIFEST
SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}
EXPECTED_CLASSDEFS = {"port", "adapter", "service", "process", "storage"}
ALLOWED_EDGE_MARKERS = ("-->", "-.->", "==>")
FORBIDDEN_EDGE_TOKENS = ("---", "--x", "x--", "<--", "<==>")
NODES_RE = re.compile(r"%%\s*@nodes\s+(\d+)")
CLASSDEF_RE = re.compile(r"^\s*classDef\s+([A-Za-z0-9_-]+)")
QUOTED_RE = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
TAG_RE = re.compile(r"<[^>]+>")


def _ensure_repo_path(path: Path) -> Path:
    resolved_root = REPO_ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(f"refusing to process path outside {resolved_root}: {resolved_path}")
    return resolved_path


def _resolve_repo_relative_path(raw: Path | str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        raise ValueError(f"absolute paths are not allowed: {candidate}")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"path traversal is not allowed: {candidate}")
    if candidate.parts and candidate.parts[0].startswith("-"):
        raise ValueError(f"option-like path is not allowed: {candidate}")
    return _ensure_repo_path(REPO_ROOT / candidate)


def _resolve_output_path(path: Path) -> Path:
    target = path if path.is_absolute() else REPO_ROOT / path
    return _ensure_repo_path(target)


def _write_report_output(path: Path, content: str) -> None:
    safe_path = _resolve_output_path(path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(content, encoding="utf-8")


@dataclass(frozen=True)
class Violation:
    file: str
    rule_id: str
    severity: str
    message: str


@dataclass(frozen=True)
class RuleSummary:
    rule_id: str
    hard_gate: bool
    passed: bool
    violations: int


@dataclass(frozen=True)
class Report:
    checked_files: int
    hard_failures: int
    warning_failures: int
    rules: list[RuleSummary]
    violations: list[Violation]


def _out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _err(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def load_manifest(manifest_path: Path) -> list[Path]:
    safe_manifest = _ensure_repo_path(manifest_path)
    if not safe_manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {safe_manifest}")
    files: list[Path] = []
    for raw in safe_manifest.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        path = _resolve_repo_relative_path(line)
        if path.suffix not in SUPPORTED_SUFFIXES:
            raise ValueError(f"Manifest entry must be .mmd/.mermaid: {line}")
        files.append(path)
    if not files:
        raise ValueError(f"Manifest has no diagram entries: {safe_manifest}")
    return files


def discover_files(targets: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []

    for target in targets:
        resolved = _ensure_repo_path(target)
        if resolved.is_file():
            if resolved.suffix in SUPPORTED_SUFFIXES and resolved not in seen:
                seen.add(resolved)
                files.append(resolved)
            continue

        if not resolved.exists():
            continue

        for pattern in ("*.mmd", "*.mermaid"):
            for candidate in resolved.rglob(pattern):
                if candidate.name.startswith("_"):
                    continue
                if "99-archive" in candidate.parts:
                    continue
                if candidate not in seen:
                    seen.add(candidate)
                    files.append(candidate)

    return sorted(files)


def parse_node_count(lines: list[str]) -> int | None:
    for line in lines:
        match = NODES_RE.search(line)
        if match:
            return int(match.group(1))
    return None


def is_flowchart(lines: list[str]) -> bool:
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        lowered = stripped.lower()
        return lowered.startswith("flowchart") or lowered.startswith("graph")
    return False


def has_edge_syntax(line: str) -> bool:
    if "linkStyle" in line or line.strip().startswith("classDef"):
        return False
    return (
        "-->" in line
        or "-.->" in line
        or "==>" in line
        or "---" in line
        or "--x" in line
    )


def normalize_label(raw: str) -> str:
    no_br = raw.replace("<br/>", " ").replace("<br>", " ")
    no_tags = TAG_RE.sub("", no_br)
    return " ".join(no_tags.split())


def check_line_style_guide(path: Path, lines: list[str]) -> list[Violation]:
    violations: list[Violation] = []
    if not is_flowchart(lines):
        return violations

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if not has_edge_syntax(stripped):
            continue

        if any(token in stripped for token in FORBIDDEN_EDGE_TOKENS):
            violations.append(
                Violation(
                    file=str(path),
                    rule_id="DIAG-T018",
                    severity="ERROR",
                    message=(
                        f"line {idx}: forbidden edge operator token detected; "
                        "allowed semantic styles are -->, -.->, ==>"
                    ),
                )
            )
            continue

        if "--" in stripped and not any(
            marker in stripped for marker in ALLOWED_EDGE_MARKERS
        ):
            violations.append(
                Violation(
                    file=str(path),
                    rule_id="DIAG-T018",
                    severity="ERROR",
                    message=(
                        f"line {idx}: edge operator is outside style guide; "
                        "use -->, -.-> or ==>"
                    ),
                )
            )

    return violations


def check_classdef_coverage(path: Path, lines: list[str]) -> list[Violation]:
    violations: list[Violation] = []
    if not is_flowchart(lines):
        return violations

    classdefs = {match.group(1) for line in lines if (match := CLASSDEF_RE.match(line))}

    if not classdefs:
        violations.append(
            Violation(
                file=str(path),
                rule_id="DIAG-T019",
                severity="WARNING",
                message="no classDef declarations found; expected typed node classes",
            )
        )
        return violations

    covered = classdefs & EXPECTED_CLASSDEFS
    if len(covered) < 2:
        violations.append(
            Violation(
                file=str(path),
                rule_id="DIAG-T019",
                severity="WARNING",
                message=(
                    "classDef coverage is low "
                    f"(found={sorted(classdefs)}, expected_any_of={sorted(EXPECTED_CLASSDEFS)})"
                ),
            )
        )
    return violations


def sibling_views_for(path: Path) -> list[Path]:
    parent = path.stem
    views_dir = source_dir("views")
    if not views_dir.exists():
        return []

    prefix = parent.split("-", maxsplit=1)[0]
    candidates = sorted(views_dir.glob(f"{prefix}-*.mermaid"))
    if candidates:
        return candidates
    return sorted(views_dir.glob(f"{parent}-*.mermaid"))


def check_large_diagram_decomposition(
    path: Path, lines: list[str], threshold: int
) -> list[Violation]:
    violations: list[Violation] = []
    nodes = parse_node_count(lines)
    if nodes is None or nodes < threshold or path.suffix != ".mmd":
        return violations

    views_dir = source_dir("views")
    views = sibling_views_for(path)
    has_full = any(view.name.endswith("-full.mermaid") for view in views)
    has_detail = any(
        any(
            token in view.name
            for token in ("-overview", "-domain", "-infra", "-dataflow")
        )
        for view in views
    )

    if not (has_full and has_detail):
        violations.append(
            Violation(
                file=str(path),
                rule_id="DIAG-T020",
                severity="ERROR",
                message=(
                    f"@nodes={nodes} requires decomposition; missing expected views in "
                    f"{views_dir.relative_to(REPO_ROOT)}"
                ),
            )
        )
    return violations


def check_large_diagram_legend(
    path: Path, lines: list[str], threshold: int
) -> list[Violation]:
    violations: list[Violation] = []
    nodes = parse_node_count(lines)
    if nodes is None or nodes < threshold:
        return violations

    content = "\n".join(lines)
    has_legend = (
        re.search(
            r"^\s*subgraph\s+Legend\b", content, flags=re.IGNORECASE | re.MULTILINE
        )
        is not None
        or "%% Legend:" in content
        or "00-legend.mermaid" in content
    )
    if not has_legend:
        violations.append(
            Violation(
                file=str(path),
                rule_id="DIAG-T021",
                severity="ERROR",
                message=f"@nodes={nodes} requires legend semantics on canvas or reference",
            )
        )
    return violations


def check_label_quality(
    path: Path, lines: list[str], max_label_length: int, max_br: int
) -> list[Violation]:
    violations: list[Violation] = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue

        for match in QUOTED_RE.finditer(stripped):
            raw = match.group(1)
            normalized = normalize_label(raw)
            if not normalized:
                continue

            if len(normalized) > max_label_length:
                violations.append(
                    Violation(
                        file=str(path),
                        rule_id="DIAG-T022",
                        severity="WARNING",
                        message=(
                            f"line {idx}: label length {len(normalized)} > {max_label_length}; "
                            "move verbose context to tooltip/click/docs"
                        ),
                    )
                )

            br_count = raw.lower().count("<br/>") + raw.lower().count("<br>")
            if br_count > max_br:
                violations.append(
                    Violation(
                        file=str(path),
                        rule_id="DIAG-T023",
                        severity="WARNING",
                        message=f"line {idx}: label has {br_count} <br/> tags (max {max_br})",
                    )
                )

    return violations


def evaluate_file(
    path: Path, *, large_threshold: int, max_label_length: int, max_br: int
) -> list[Violation]:
    try:
        safe_path = _ensure_repo_path(path)
        lines = safe_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [
            Violation(
                file=str(path),
                rule_id="DIAG-T018",
                severity="ERROR",
                message=f"failed to read file: {exc}",
            )
        ]

    violations: list[Violation] = []
    violations.extend(check_line_style_guide(path, lines))
    violations.extend(check_classdef_coverage(path, lines))
    violations.extend(
        check_large_diagram_decomposition(path, lines, threshold=large_threshold)
    )
    violations.extend(
        check_large_diagram_legend(path, lines, threshold=large_threshold)
    )
    violations.extend(
        check_label_quality(
            path, lines, max_label_length=max_label_length, max_br=max_br
        )
    )
    return violations


def summarize(violations: list[Violation]) -> list[RuleSummary]:
    hard_rules = {"DIAG-T018", "DIAG-T020", "DIAG-T021"}
    all_rules = [
        "DIAG-T018",
        "DIAG-T019",
        "DIAG-T020",
        "DIAG-T021",
        "DIAG-T022",
        "DIAG-T023",
    ]
    by_rule: dict[str, list[Violation]] = {rule: [] for rule in all_rules}

    for violation in violations:
        by_rule.setdefault(violation.rule_id, []).append(violation)

    summaries: list[RuleSummary] = []
    for rule in all_rules:
        issues = by_rule.get(rule, [])
        summaries.append(
            RuleSummary(
                rule_id=rule,
                hard_gate=rule in hard_rules,
                passed=not issues,
                violations=len(issues),
            )
        )
    return summaries


def render_markdown(report: Report) -> str:
    lines: list[str] = []
    lines.append("# Diagram Regression Quality Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Checked files: {report.checked_files}")
    lines.append(f"- Hard failures: {report.hard_failures}")
    lines.append(f"- Warning failures: {report.warning_failures}")
    lines.append("")
    lines.append("## Rule Status")
    lines.append("")
    lines.append("| Rule | Gate | Status | Violations |")
    lines.append("|---|---|---|---:|")
    for item in report.rules:
        gate = "Hard" if item.hard_gate else "Soft"
        status = "PASS" if item.passed else "FAIL"
        lines.append(f"| {item.rule_id} | {gate} | {status} | {item.violations} |")

    if report.violations:
        lines.append("")
        lines.append("## Violations")
        lines.append("")
        for violation in report.violations:
            lines.append(
                f"- `{violation.rule_id}` [{violation.severity}] {violation.file}: {violation.message}"
            )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run diagram regression quality gates")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Diagram files/directories to check (ignored when --manifest is used)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Path to source manifest (default: {DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="Ignore manifest and evaluate paths/default target discovery",
    )
    parser.add_argument(
        "--large-threshold",
        type=int,
        default=30,
        help="Node threshold for large-diagram checks (default: 30)",
    )
    parser.add_argument(
        "--max-label-length",
        type=int,
        default=90,
        help="Max normalized label length before warning (default: 90)",
    )
    parser.add_argument(
        "--max-br",
        type=int,
        default=4,
        help="Max <br/> tags per label before warning (default: 4)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Write JSON report to file",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        help="Write markdown report to file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON report to stdout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if not args.no_manifest:
            manifest = (
                DEFAULT_MANIFEST
                if args.manifest == DEFAULT_MANIFEST
                else _resolve_repo_relative_path(args.manifest)
            )
            files = load_manifest(manifest)
        else:
            targets = (
                [_resolve_repo_relative_path(path) for path in args.paths]
                if args.paths
                else [DEFAULT_TARGET]
            )
            files = discover_files(targets)
    except (FileNotFoundError, ValueError) as exc:
        _err(f"[ERROR] {exc}")
        return 2

    if not files:
        _err("[ERROR] No diagram files resolved for quality-gate check.")
        return 2

    violations: list[Violation] = []
    for file_path in files:
        violations.extend(
            evaluate_file(
                file_path,
                large_threshold=args.large_threshold,
                max_label_length=args.max_label_length,
                max_br=args.max_br,
            )
        )

    summaries = summarize(violations)
    hard_failures = sum(
        1
        for violation in violations
        if violation.rule_id in {"DIAG-T018", "DIAG-T020", "DIAG-T021"}
    )
    warning_failures = len(violations) - hard_failures

    report = Report(
        checked_files=len(files),
        hard_failures=hard_failures,
        warning_failures=warning_failures,
        rules=summaries,
        violations=violations,
    )

    try:
        if args.json_out is not None:
            _write_report_output(
                args.json_out,
                json.dumps(
                    {
                        "checked_files": report.checked_files,
                        "hard_failures": report.hard_failures,
                        "warning_failures": report.warning_failures,
                        "rules": [asdict(item) for item in report.rules],
                        "violations": [asdict(item) for item in report.violations],
                    },
                    indent=2,
                    ensure_ascii=True,
                )
                + "\n",
            )

        if args.markdown_out is not None:
            _write_report_output(args.markdown_out, render_markdown(report))
    except ValueError as exc:
        _err(f"[ERROR] {exc}")
        return 2

    if args.json:
        _out(
            json.dumps(
                {
                    "checked_files": report.checked_files,
                    "hard_failures": report.hard_failures,
                    "warning_failures": report.warning_failures,
                    "rules": [asdict(item) for item in report.rules],
                    "violations": [asdict(item) for item in report.violations],
                },
                indent=2,
                ensure_ascii=True,
            )
        )
    else:
        _out(
            "[INFO] Diagram quality gates: "
            f"checked={report.checked_files}, hard_failures={report.hard_failures}, "
            f"warnings={report.warning_failures}"
        )
        for rule in report.rules:
            gate = "HARD" if rule.hard_gate else "SOFT"
            status = "PASS" if rule.passed else "FAIL"
            _out(f"[INFO] {rule.rule_id} [{gate}] {status} ({rule.violations})")

    return 1 if report.hard_failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
