#!/usr/bin/env python3
"""Generate a report-only inventory of exact and near-duplicate dashboard PromQL."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_DASHBOARDS_DIR = Path("grafana/dashboards")
_DEFAULT_ALLOWLIST = Path("configs/quality/dashboard_query_duplicate_allowlist.yaml")
_METRIC_RE = re.compile(r"\bbioetl_[a-z0-9_]+\b")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_STRING_RE = re.compile(r'"[^"]*"')
_SELECTOR_RE = re.compile(r"\{[^{}]*\}")


@dataclass(frozen=True)
class QueryUse:
    """One dashboard query usage site."""

    dashboard: str
    panel_title: str
    target_ref: str
    expression: str


@dataclass(frozen=True)
class ExactDuplicateGroup:
    """One exact-duplicate PromQL group."""

    expression: str
    uses: tuple[QueryUse, ...]
    scope: str
    dashboards: tuple[str, ...]
    panel_refs: tuple[str, ...]


@dataclass(frozen=True)
class NearDuplicateGroup:
    """One near-duplicate PromQL family."""

    signature: str
    metrics: tuple[str, ...]
    distinct_expressions: tuple[str, ...]
    uses: tuple[QueryUse, ...]
    scope: str
    dashboards: tuple[str, ...]
    panel_refs: tuple[str, ...]


@dataclass(frozen=True)
class GovernanceViolation:
    """One duplicate-query governance violation."""

    kind: str
    scope: str
    panel_refs: tuple[str, ...]
    message: str


def _normalize_expression(expr: str) -> str:
    """Collapse expression whitespace for stable equality comparisons."""
    return " ".join(expr.split())


def _shape_expression_for_near_duplicates(expr: str) -> str:
    """Build a coarse query-family signature for near-duplicate grouping."""
    shaped = _normalize_expression(expr)
    shaped = _STRING_RE.sub('"?"', shaped)
    shaped = _SELECTOR_RE.sub("{}", shaped)
    shaped = _NUMBER_RE.sub("?", shaped)
    return re.sub(r"\s+", " ", shaped).strip()


def _extract_metrics(expr: str) -> tuple[str, ...]:
    """Return the distinct BioETL metric names referenced by the expression."""
    return tuple(sorted(set(_METRIC_RE.findall(expr))))


def _walk_panels(panels: list[dict]) -> list[dict]:
    """Flatten dashboard panels, including nested row-contained panels."""
    flattened: list[dict] = []
    for panel in panels:
        flattened.append(panel)
        nested = panel.get("panels", [])
        if isinstance(nested, list):
            flattened.extend(_walk_panels(nested))
    return flattened


def _classify_scope(uses: tuple[QueryUse, ...]) -> str:
    """Classify how broadly a query family is reused."""
    panel_refs = {(use.dashboard, use.panel_title) for use in uses}
    dashboard_names = {use.dashboard for use in uses}
    if len(panel_refs) == 1:
        return "single_panel_multi_target"
    if len(dashboard_names) == 1:
        return "single_dashboard_multi_panel"
    return "cross_dashboard"


def _sorted_uses(uses: list[QueryUse] | set[QueryUse]) -> tuple[QueryUse, ...]:
    """Return query uses in stable dashboard/panel/target order."""
    return tuple(
        sorted(
            uses,
            key=lambda item: (
                item.dashboard,
                item.panel_title,
                item.target_ref,
                item.expression,
            ),
        )
    )


def _panel_refs(uses: tuple[QueryUse, ...]) -> tuple[str, ...]:
    """Return stable dashboard/panel references for human-facing summaries."""
    return tuple(sorted({f"{use.dashboard} :: {use.panel_title}" for use in uses}))


def collect_panel_query_uses(
    dashboards_dir: Path = _DASHBOARDS_DIR,
) -> tuple[QueryUse, ...]:
    """Collect PromQL expressions from dashboard panel targets."""
    query_uses: list[QueryUse] = []
    for dashboard_path in sorted(dashboards_dir.glob("*.json")):
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
        panels = _walk_panels(list(dashboard.get("panels", [])))
        for row in dashboard.get("rows", []):
            panels.extend(_walk_panels(row.get("panels", [])))
        for panel in panels:
            title = panel.get("title")
            if not isinstance(title, str):
                continue
            for index, target in enumerate(panel.get("targets", []), start=1):
                expr = target.get("expr")
                if not isinstance(expr, str) or not expr.strip():
                    continue
                query_uses.append(
                    QueryUse(
                        dashboard=dashboard_path.name,
                        panel_title=title,
                        target_ref=f"target[{index}]",
                        expression=_normalize_expression(expr),
                    )
                )
    return tuple(query_uses)


def build_exact_duplicate_groups(
    query_uses: tuple[QueryUse, ...],
) -> tuple[ExactDuplicateGroup, ...]:
    """Group exact duplicate expressions used more than once."""
    uses_by_expression: dict[str, list[QueryUse]] = {}
    for use in query_uses:
        uses_by_expression.setdefault(use.expression, []).append(use)

    groups: list[ExactDuplicateGroup] = []
    for expression, grouped_uses in uses_by_expression.items():
        if len(grouped_uses) < 2:
            continue
        uses = _sorted_uses(grouped_uses)
        groups.append(
            ExactDuplicateGroup(
                expression=expression,
                uses=uses,
                scope=_classify_scope(uses),
                dashboards=tuple(sorted({use.dashboard for use in uses})),
                panel_refs=_panel_refs(uses),
            )
        )

    return tuple(
        sorted(
            groups,
            key=lambda item: (
                item.scope,
                -len(item.uses),
                item.expression,
            ),
        )
    )


def build_near_duplicate_groups(
    query_uses: tuple[QueryUse, ...],
    *,
    include_single_panel: bool = False,
) -> tuple[NearDuplicateGroup, ...]:
    """Group similar query shapes used in more than one distinct expression."""
    uses_by_signature: dict[str, list[QueryUse]] = {}
    for use in query_uses:
        uses_by_signature.setdefault(
            _shape_expression_for_near_duplicates(use.expression), []
        ).append(use)

    groups: list[NearDuplicateGroup] = []
    for signature, grouped_uses in uses_by_signature.items():
        distinct_expressions = tuple(sorted({use.expression for use in grouped_uses}))
        if len(grouped_uses) < 2 or len(distinct_expressions) < 2:
            continue

        uses = _sorted_uses(grouped_uses)
        scope = _classify_scope(uses)
        if not include_single_panel and scope == "single_panel_multi_target":
            continue

        metrics = tuple(
            sorted(
                {
                    metric
                    for expression in distinct_expressions
                    for metric in _extract_metrics(expression)
                }
            )
        )
        groups.append(
            NearDuplicateGroup(
                signature=signature,
                metrics=metrics,
                distinct_expressions=distinct_expressions,
                uses=uses,
                scope=scope,
                dashboards=tuple(sorted({use.dashboard for use in uses})),
                panel_refs=_panel_refs(uses),
            )
        )

    return tuple(
        sorted(
            groups,
            key=lambda item: (
                item.scope,
                -len(item.panel_refs),
                -len(item.uses),
                item.signature,
            ),
        )
    )


def _build_payload(
    *,
    exact_duplicates: tuple[ExactDuplicateGroup, ...],
    near_duplicates: tuple[NearDuplicateGroup, ...],
    violations: tuple[GovernanceViolation, ...] = (),
) -> dict[str, object]:
    """Build machine-readable report payload."""
    return {
        "summary": {
            "exact_duplicate_groups": len(exact_duplicates),
            "near_duplicate_groups": len(near_duplicates),
            "governance_violations": len(violations),
            "cross_dashboard_exact_groups": sum(
                1 for group in exact_duplicates if group.scope == "cross_dashboard"
            ),
            "cross_dashboard_near_groups": sum(
                1 for group in near_duplicates if group.scope == "cross_dashboard"
            ),
        },
        "exact_duplicates": [asdict(group) for group in exact_duplicates],
        "near_duplicates": [asdict(group) for group in near_duplicates],
        "violations": [asdict(violation) for violation in violations],
    }


def _load_allowlist(path: Path) -> dict[str, object]:
    import yaml

    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(
            f"Dashboard query duplicate allowlist must be a mapping: {path}"
        )
    return payload


def _allowed_exact_panel_refs(policy: dict[str, object]) -> set[tuple[str, ...]]:
    exact = policy.get("exact_duplicates")
    if not isinstance(exact, dict):
        return set()
    groups = exact.get("allowed_groups")
    if not isinstance(groups, list):
        return set()
    allowed: set[tuple[str, ...]] = set()
    for item in groups:
        if not isinstance(item, dict):
            continue
        panel_refs = item.get("panel_refs")
        if not isinstance(panel_refs, list):
            continue
        refs = tuple(sorted(str(ref) for ref in panel_refs if str(ref).strip()))
        if refs:
            allowed.add(refs)
    return allowed


def _near_duplicate_max_count(policy: dict[str, object]) -> int | None:
    near = policy.get("near_duplicates")
    if not isinstance(near, dict):
        return None
    value = near.get("max_count")
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def evaluate_governance(
    *,
    exact_duplicates: tuple[ExactDuplicateGroup, ...],
    near_duplicates: tuple[NearDuplicateGroup, ...],
    allowlist_path: Path = _DEFAULT_ALLOWLIST,
) -> tuple[GovernanceViolation, ...]:
    """Evaluate duplicate-query groups against the reviewed allowlist/budget."""
    policy = _load_allowlist(allowlist_path)
    allowed_exact_refs = _allowed_exact_panel_refs(policy)
    near_max_count = _near_duplicate_max_count(policy)
    violations: list[GovernanceViolation] = []

    for group in exact_duplicates:
        if tuple(sorted(group.panel_refs)) in allowed_exact_refs:
            continue
        violations.append(
            GovernanceViolation(
                kind="unreviewed_exact_duplicate",
                scope=group.scope,
                panel_refs=group.panel_refs,
                message="Exact duplicate query group is not declared in allowlist",
            )
        )

    if near_max_count is not None and len(near_duplicates) > near_max_count:
        violations.append(
            GovernanceViolation(
                kind="near_duplicate_budget_exceeded",
                scope="global",
                panel_refs=(),
                message=(
                    "Near duplicate query groups exceed budget "
                    f"({len(near_duplicates)} > {near_max_count})"
                ),
            )
        )
    return tuple(violations)


def _render_markdown(
    *,
    exact_duplicates: tuple[ExactDuplicateGroup, ...],
    near_duplicates: tuple[NearDuplicateGroup, ...],
    include_single_panel: bool,
) -> str:
    """Render a human-readable markdown summary."""
    lines = [
        "# Dashboard Query Duplicate Report",
        "",
        f"- exact_duplicate_groups: {len(exact_duplicates)}",
        f"- near_duplicate_groups: {len(near_duplicates)}",
        f"- near_duplicate_scope: {'all panels' if include_single_panel else 'cross-panel only'}",
        "",
        "## Exact Duplicate Groups",
        "",
    ]

    if not exact_duplicates:
        lines.append("- None.")
    else:
        for group in exact_duplicates:
            lines.extend(
                [
                    f"### Scope: `{group.scope}`",
                    "",
                    f"- uses: {len(group.uses)}",
                    f"- dashboards: {', '.join(group.dashboards)}",
                    f"- expression: `{group.expression}`",
                    "- panel_refs:",
                ]
            )
            lines.extend(f"  - `{panel_ref}`" for panel_ref in group.panel_refs)
            lines.append("")

    lines.extend(["## Near-Duplicate Families", ""])
    if not near_duplicates:
        lines.append("- None.")
    else:
        for group in near_duplicates:
            lines.extend(
                [
                    f"### Scope: `{group.scope}`",
                    "",
                    f"- dashboards: {', '.join(group.dashboards)}",
                    f"- metrics: {', '.join(group.metrics) or '(none inferred)'}",
                    f"- distinct_expressions: {len(group.distinct_expressions)}",
                    f"- signature: `{group.signature}`",
                    "- panel_refs:",
                ]
            )
            lines.extend(f"  - `{panel_ref}`" for panel_ref in group.panel_refs)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run the dashboard query duplicate report CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON to stdout.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for JSON output.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        help="Optional path for markdown output.",
    )
    parser.add_argument(
        "--include-single-panel-near",
        action="store_true",
        help=(
            "Include near-duplicate groups that only appear as multi-target "
            "variants inside one panel (for example p50/p95/p99 triplets)."
        ),
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=_DEFAULT_ALLOWLIST,
        help="Reviewed duplicate-query allowlist/budget YAML.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when live duplicate groups are not covered by allowlist/budget.",
    )
    args = parser.parse_args(argv)

    query_uses = collect_panel_query_uses()
    exact_duplicates = build_exact_duplicate_groups(query_uses)
    near_duplicates = build_near_duplicate_groups(
        query_uses,
        include_single_panel=args.include_single_panel_near,
    )
    try:
        violations = evaluate_governance(
            exact_duplicates=exact_duplicates,
            near_duplicates=near_duplicates,
            allowlist_path=args.allowlist,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    payload = _build_payload(
        exact_duplicates=exact_duplicates,
        near_duplicates=near_duplicates,
        violations=violations,
    )
    markdown = _render_markdown(
        exact_duplicates=exact_duplicates,
        near_duplicates=near_duplicates,
        include_single_panel=args.include_single_panel_near,
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(markdown, end="")

    if args.json_out is not None:
        args.json_out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.markdown_out is not None:
        args.markdown_out.write_text(markdown, encoding="utf-8")

    if args.check and violations:
        for violation in violations:
            refs = ", ".join(violation.panel_refs) or "(global)"
            print(
                f"[FAIL] {violation.kind}: {violation.message}: {refs}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
