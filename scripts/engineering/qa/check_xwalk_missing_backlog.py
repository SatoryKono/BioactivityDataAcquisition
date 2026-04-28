#!/usr/bin/env python3
"""Validate that xwalk MISSING_* markers are tracked in the backlog."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    raise RuntimeError("PyYAML is required to validate the xwalk backlog") from exc

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_XWALK_ROOT = REPO_ROOT / "docs/04-reference/pipelines"
DEFAULT_BACKLOG_PATH = REPO_ROOT / "configs/quality/xwalk_missing_backlog.yaml"
MARKER_KINDS = frozenset(
    {"MISSING_CODE", "MISSING_DOC", "MISSING_GOLD", "MISSING_TRANSFORMER"}
)
CLASSIFICATION_VALUES = frozenset({"must_fix", "should_fix", "deferred"})
MARKER_RE = re.compile(r"\bMISSING_(?:CODE|DOC|GOLD|TRANSFORMER)\b")


@dataclass(frozen=True, order=True)
class XwalkMissingFinding:
    """A single missing marker found in an xwalk row."""

    path: str
    provider: str
    entity: str
    field: str
    marker: str


@dataclass(frozen=True)
class BacklogRule:
    """Expected backlog coverage for one xwalk file and marker kind."""

    path: str
    marker: str
    classification: str
    owner_issue: str
    rationale: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class BacklogValidation:
    """Validation result for the current xwalk backlog."""

    findings: tuple[XwalkMissingFinding, ...]
    rules: tuple[BacklogRule, ...]
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _provider_entity(path: Path) -> tuple[str, str]:
    provider = path.parent.name
    entity = path.name.removesuffix("-xwalk.csv")
    return provider, entity


def _field_name(row: Mapping[str, str | None]) -> str:
    for key in ("field", "field_name", "name"):
        value = row.get(key)
        if value:
            return value
    return "<missing-field-column>"


def collect_xwalk_missing_findings(
    xwalk_root: Path = DEFAULT_XWALK_ROOT,
) -> tuple[XwalkMissingFinding, ...]:
    """Return all tracked MISSING_* markers from xwalk CSV files."""

    root = _resolve_path(xwalk_root)
    findings: list[XwalkMissingFinding] = []
    for path in sorted(root.rglob("*-xwalk.csv")):
        provider, entity = _provider_entity(path)
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                row_values = " ".join(str(value or "") for value in row.values())
                markers = sorted(set(MARKER_RE.findall(row_values)))
                if not markers:
                    continue
                field = _field_name(row)
                rel_path = _display_path(path)
                findings.extend(
                    XwalkMissingFinding(
                        path=rel_path,
                        provider=provider,
                        entity=entity,
                        field=field,
                        marker=marker,
                    )
                    for marker in markers
                )
    return tuple(sorted(findings))


def load_backlog(path: Path = DEFAULT_BACKLOG_PATH) -> dict[str, Any]:
    """Load the xwalk missing backlog YAML file."""

    backlog_path = _resolve_path(path)
    raw = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{backlog_path} must contain a YAML mapping")
    return cast(dict[str, Any], raw)


def _require_str_list(value: Any, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of strings")
    return tuple(cast(list[str], value))


def _resolve_allowed_marker_kinds(backlog: Mapping[str, Any]) -> set[str]:
    """Resolve the configured set of allowed MISSING_* marker kinds."""
    return set(
        _require_str_list(
            backlog.get("marker_kinds", sorted(MARKER_KINDS)),
            label="marker_kinds",
        )
    )


def _resolve_allowed_classification_values(backlog: Mapping[str, Any]) -> set[str]:
    """Resolve the configured set of allowed backlog classifications."""
    return set(
        _require_str_list(
            backlog.get("classification_values", sorted(CLASSIFICATION_VALUES)),
            label="classification_values",
        )
    )


def _require_rule_path_and_markers(
    raw_rule: Mapping[str, Any],
    *,
    rule_number: int,
) -> tuple[str, dict[str, Any]]:
    """Validate one raw rule envelope and return normalized path/marker mapping."""
    path = raw_rule.get("path")
    markers = raw_rule.get("markers")
    if not isinstance(path, str) or not path:
        raise ValueError(f"rules[{rule_number}].path must be a non-empty string")
    if not isinstance(markers, dict):
        raise ValueError(f"rules[{rule_number}].markers must be a mapping")
    return path, cast(dict[str, Any], markers)


def _build_backlog_rule(
    *,
    path: str,
    marker: str,
    raw_marker_rule: Mapping[str, Any],
    marker_kinds: set[str],
    classification_values: set[str],
) -> BacklogRule:
    """Validate and build one backlog rule for one path/marker pair."""
    if marker not in marker_kinds:
        raise ValueError(f"{path}:{marker} is not in marker_kinds")
    if not isinstance(raw_marker_rule, dict):
        raise ValueError(f"{path}:{marker} rule must be a mapping")

    fields = _require_str_list(
        raw_marker_rule.get("fields", []),
        label=f"{path}:{marker}.fields",
    )
    classification = raw_marker_rule.get("classification")
    owner_issue = raw_marker_rule.get("owner_issue")
    rationale = raw_marker_rule.get("rationale", "")
    if classification not in classification_values:
        raise ValueError(f"{path}:{marker}.classification is not allowed")
    if owner_issue in {None, ""}:
        raise ValueError(f"{path}:{marker}.owner_issue is required")
    if not isinstance(rationale, str) or not rationale:
        raise ValueError(f"{path}:{marker}.rationale is required")

    return BacklogRule(
        path=path,
        marker=marker,
        classification=cast(str, classification),
        owner_issue=str(owner_issue),
        rationale=rationale,
        fields=fields,
    )


def _build_rule_index(backlog: Mapping[str, Any]) -> dict[tuple[str, str], BacklogRule]:
    marker_kinds = _resolve_allowed_marker_kinds(backlog)
    classification_values = _resolve_allowed_classification_values(backlog)
    raw_rules = backlog.get("rules", [])
    if not isinstance(raw_rules, list):
        raise ValueError("rules must be a list")

    rule_index: dict[tuple[str, str], BacklogRule] = {}
    for rule_number, raw_rule in enumerate(raw_rules, start=1):
        if not isinstance(raw_rule, dict):
            raise ValueError(f"rules[{rule_number}] must be a mapping")
        path, markers = _require_rule_path_and_markers(
            raw_rule,
            rule_number=rule_number,
        )

        for marker, raw_marker_rule in markers.items():
            rule = _build_backlog_rule(
                path=path,
                marker=marker,
                raw_marker_rule=cast(Mapping[str, Any], raw_marker_rule),
                marker_kinds=marker_kinds,
                classification_values=classification_values,
            )
            key = (path, marker)
            if key in rule_index:
                raise ValueError(f"Duplicate backlog rule for {path}:{marker}")
            rule_index[key] = rule

    return rule_index


def _counter_index(
    findings: Iterable[XwalkMissingFinding],
) -> dict[tuple[str, str], Counter[str]]:
    index: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for finding in findings:
        index[(finding.path, finding.marker)][finding.field] += 1
    return dict(index)


def validate_backlog(
    *,
    xwalk_root: Path = DEFAULT_XWALK_ROOT,
    backlog_path: Path = DEFAULT_BACKLOG_PATH,
) -> BacklogValidation:
    """Validate current xwalk markers against the committed backlog."""

    findings = collect_xwalk_missing_findings(xwalk_root)
    backlog = load_backlog(backlog_path)
    rule_index = _build_rule_index(backlog)
    actual_index = _counter_index(findings)
    expected_index = {
        key: Counter(rule.fields) for key, rule in rule_index.items()
    }

    errors: list[str] = []
    for key in sorted(actual_index.keys() - expected_index.keys()):
        path, marker = key
        fields = ", ".join(sorted(actual_index[key]))
        errors.append(f"Untracked {marker} in {path}: {fields}")

    for key in sorted(expected_index.keys() - actual_index.keys()):
        path, marker = key
        fields = ", ".join(sorted(expected_index[key]))
        errors.append(f"Backlog rule no longer matches any {marker} in {path}: {fields}")

    for key in sorted(actual_index.keys() & expected_index.keys()):
        actual = actual_index[key]
        expected = expected_index[key]
        if actual == expected:
            continue
        path, marker = key
        added = actual - expected
        removed = expected - actual
        if added:
            errors.append(
                f"New unclassified {marker} in {path}: {', '.join(sorted(added))}"
            )
        if removed:
            errors.append(
                f"Resolved {marker} still listed in backlog for {path}: "
                f"{', '.join(sorted(removed))}"
            )

    return BacklogValidation(
        findings=findings,
        rules=tuple(sorted(rule_index.values(), key=lambda rule: (rule.path, rule.marker))),
        errors=tuple(errors),
    )


def _build_payload(validation: BacklogValidation) -> dict[str, object]:
    findings = validation.findings
    rules = validation.rules
    marker_counts = Counter(finding.marker for finding in findings)
    file_counts = Counter(finding.path for finding in findings)
    classification_counts = Counter(rule.classification for rule in rules)
    owner_issue_counts = Counter(rule.owner_issue for rule in rules)
    rule_lookup = {(rule.path, rule.marker): rule for rule in rules}

    entries = []
    for finding in findings:
        rule = rule_lookup.get((finding.path, finding.marker))
        entries.append(
            {
                "path": finding.path,
                "provider": finding.provider,
                "entity": finding.entity,
                "field": finding.field,
                "marker": finding.marker,
                "classification": rule.classification if rule else None,
                "owner_issue": rule.owner_issue if rule else None,
            }
        )

    return {
        "ok": validation.ok,
        "scope": "xwalk_missing_backlog",
        "xwalk_file_count": len(file_counts),
        "missing_marker_count": len(findings),
        "tracked_rule_count": len(rules),
        "marker_counts": dict(sorted(marker_counts.items())),
        "classification_counts": dict(sorted(classification_counts.items())),
        "owner_issue_counts": dict(sorted(owner_issue_counts.items())),
        "errors": list(validation.errors),
        "entries": entries,
    }


def _render_markdown(payload: Mapping[str, object], *, limit: int) -> str:
    lines = [
        "# Xwalk Missing Backlog",
        "",
        f"- ok: `{payload['ok']}`",
        f"- scope: `{payload['scope']}`",
        f"- xwalk_file_count: `{payload['xwalk_file_count']}`",
        f"- missing_marker_count: `{payload['missing_marker_count']}`",
        f"- tracked_rule_count: `{payload['tracked_rule_count']}`",
        "",
        "## Marker Counts",
        "",
    ]
    for marker, count in cast(dict[str, int], payload["marker_counts"]).items():
        lines.append(f"- `{marker}`: `{count}`")

    lines.extend(["", "## Classifications", ""])
    for classification, count in cast(
        dict[str, int], payload["classification_counts"]
    ).items():
        lines.append(f"- `{classification}`: `{count}`")

    errors = cast(list[str], payload["errors"])
    if errors:
        lines.extend(["", "## Errors", ""])
        for error in errors[:limit]:
            lines.append(f"- {error}")
    else:
        lines.extend(["", "No backlog drift detected."])

    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--xwalk-root",
        type=Path,
        default=DEFAULT_XWALK_ROOT,
        help="Root directory containing *-xwalk.csv files",
    )
    parser.add_argument(
        "--backlog",
        type=Path,
        default=DEFAULT_BACKLOG_PATH,
        help="YAML backlog that classifies current MISSING_* markers",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path for machine-readable JSON output",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Optional path for Markdown output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of drift errors to render in Markdown (default: 20)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    validation = validate_backlog(
        xwalk_root=args.xwalk_root,
        backlog_path=args.backlog,
    )
    payload = _build_payload(validation)

    if args.json_out is not None:
        _write_text(args.json_out, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.markdown_out is not None:
        _write_text(args.markdown_out, _render_markdown(payload, limit=args.limit) + "\n")

    if validation.ok:
        print(
            "xwalk missing backlog OK: "
            f"{payload['missing_marker_count']} marker instances across "
            f"{payload['xwalk_file_count']} xwalk files are tracked"
        )
        return 0

    for error in validation.errors:
        print(error, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
