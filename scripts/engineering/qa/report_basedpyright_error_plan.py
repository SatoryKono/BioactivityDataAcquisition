#!/usr/bin/env python3
"""Turn a basedpyright ``--outputjson`` dump into an exact, RF-mapped error plan.

Project Diagnostics helper (see
``docs/00-project/ai/agents/guides/BASEDPRIGHT_PROJECT_DIAGNOSTICS.md`` and
``reports/quality/PROJECT_DIAGNOSTICS_REMEDIATION_PLAN_2026-08-14.md``).

The command buckets ``severity == error`` diagnostics by ``(rule, tree)`` and by
``(rule, file)``, maps each rule to a remediation workstream (``RF-00x``) plus a
structural fix recipe, and writes a deterministic Markdown + JSON plan. It is
read-only against the codebase (only reads the basedpyright JSON, only writes the
two report artifacts) and therefore safe to run without a type checker present.

Usage::

    basedpyright --outputjson > reports/bp_workspace_live.json
    python -m scripts.engineering.qa.report_basedpyright_error_plan \
        --source reports/bp_workspace_live.json

    # product-only view (errors must stay 0):
    basedpyright --outputjson src/bioetl > reports/bp_product_live.json
    python -m scripts.engineering.qa.report_basedpyright_error_plan \
        --source reports/bp_product_live.json --label product
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path("reports/bp_workspace_live.json")
DEFAULT_OUT_MD = Path("reports/quality/project-diagnostics-error-plan.md")
DEFAULT_OUT_JSON = Path("reports/quality/project-diagnostics-error-plan.json")


@dataclass(frozen=True)
class RulePlan:
    """Remediation mapping for a single basedpyright rule."""

    rf: str
    default_severity: str
    cause: str
    fix: str
    validation: str


# Rule -> workstream + structural fix recipe. Grounded in the suppressions this
# repository actually carries (``# pyright: ignore[...]`` across ``src/bioetl``).
RULE_PLAN: dict[str, RulePlan] = {
    "reportArgumentType": RulePlan(
        "RF-003",
        "error",
        "Port|None / loosely typed kwargs passed into constructors, factories, or "
        "Click decorators.",
        "Give precise parameter types / Protocol params; narrow None before the "
        "call; use typed Click decorator wrappers. Remove the paired "
        "`# type: ignore[arg-type]` in the same edit.",
        "mypy --strict green on the touched module; basedpyright reportArgumentType count down.",
    ),
    "reportCallIssue": RulePlan(
        "RF-004",
        "error",
        "Hook callables typed as object/Any so pyright cannot prove they are callable.",
        "Type hook params as Callable[..., T] or a Protocol; drop `# type: ignore[operator]`.",
        "backend/startup unit tests; reportCallIssue count down.",
    ),
    "reportInvalidCast": RulePlan(
        "RF-002",
        "error",
        "`cast(_XHostProtocol, self)` mixin pattern where self is not statically "
        "the host protocol.",
        "Make the class structurally implement the Host Protocol (or add a Protocol "
        "base + typing.Self) so the cast is valid or unneeded.",
        "mypy green; reportInvalidCast count down.",
    ),
    "reportAttributeAccessIssue": RulePlan(
        "RF-005",
        "error",
        "pyarrow.compute (pc.equal/pc.and_) and httpx response attributes under "
        "incomplete local stubs.",
        "Complete configs/typing-stubs/pyarrow via the schema stub generator; add "
        "typed wrappers for httpx response access. No bulk hand-edit of schemas.",
        "schema/golden tests; determinism preserved; rule count down.",
    ),
    "reportPossiblyUnbound": RulePlan(
        "RF-007",
        "error",
        "Optional dependency imported inside try/except then used unconditionally "
        "(e.g. OpenTelemetry in observability/tracing.py).",
        "Initialize to None + guard usage, or import at module top with explicit typing.",
        "tracing/quarantine unit tests; rule count down.",
    ),
    "reportIncompatibleMethodOverride": RulePlan(
        "RF-006",
        "error",
        "Mixin/Protocol layering: override method signature does not match the base.",
        "Align override signatures; prefer Protocol over concrete base; fix variance.",
        "mypy green; rule count down.",
    ),
    "reportIncompatibleVariableOverride": RulePlan(
        "RF-006",
        "error",
        "Attribute re-declared with an incompatible/narrower type across mixins.",
        "Unify the declared attribute type or move it to a single Protocol owner.",
        "mypy green; rule count down.",
    ),
    "reportGeneralTypeIssues": RulePlan(
        "RF-003",
        "error",
        "Loose dict/item typing at a boundary.",
        "Introduce TypedDict / explicit conversions at the boundary.",
        "unit tests; rule count down.",
    ),
    "reportReturnType": RulePlan(
        "RF-007",
        "error",
        "Return value does not match the annotated return type (often tests/scripts).",
        "Tighten the return expression or the annotation to match reality.",
        "mypy on the touched tree; rule count down.",
    ),
    "reportIndexIssue": RulePlan(
        "RF-007",
        "error",
        "Indexing a value whose type does not support subscription.",
        "Narrow the container type or guard before indexing.",
        "mypy on the touched tree; rule count down.",
    ),
    "reportOptionalMemberAccess": RulePlan(
        "RF-007",
        "error",
        "Member access on a possibly-None value.",
        "Add an `is not None` guard or restructure so the value is non-optional.",
        "mypy on the touched tree; rule count down.",
    ),
    "reportRedeclaration": RulePlan(
        "RF-007",
        "error",
        "Symbol re-declared with a different type in the same scope.",
        "Rename or unify the declaration.",
        "mypy on the touched tree; rule count down.",
    ),
    "reportAssignmentType": RulePlan(
        "RF-007",
        "error",
        "Assigned value type does not match the declared target type.",
        "Fix the value or the declared type; avoid re-suppressing.",
        "mypy on the touched tree; rule count down.",
    ),
    "reportUninitializedInstanceVariable": RulePlan(
        "RF-006",
        "warning",
        "Class-level attribute declared but initialized in a mixin/host, not __init__.",
        "Initialize the attribute, use dataclasses.field(init=False), or annotate in __init__.",
        "advisory; rule count down (no growth).",
    ),
    "reportImplicitAbstractClass": RulePlan(
        "RF-007",
        "warning",
        "Class implicitly abstract via an unimplemented protocol member.",
        "Make abstractness explicit (ABC/@abstractmethod) or implement the member.",
        "advisory; rule count down.",
    ),
    "reportUnsafeMultipleInheritance": RulePlan(
        "RF-007",
        "warning",
        "Multiple inheritance with conflicting __init__/base semantics.",
        "Refactor to a single base + mixins with compatible signatures.",
        "advisory; rule count down.",
    ),
    "reportMissingModuleSource": RulePlan(
        "RF-007",
        "warning",
        "Third-party module present but without type information (e.g. openpyxl).",
        "Add/point to stubs (stubPath) or a typed shim.",
        "advisory; rule count down.",
    ),
    "reportPossiblyUnboundVariable": RulePlan(
        "RF-007",
        "error",
        "Alias of reportPossiblyUnbound; conditional bind then use.",
        "Initialize to None + guard, or lift the import/assignment.",
        "unit tests; rule count down.",
    ),
}

_GENERIC_PLAN = RulePlan(
    "RF-007",
    "unknown",
    "Not yet mapped to a workstream — inspect the message and file.",
    "Fix structurally at the source; never re-suppress. Prefer Host Protocols over "
    "cast(Any, None). Do not raise any debt budget.",
    "mypy --strict green on the touched module; rule count down vs baseline.",
)


def _tree_of(file_path: str) -> str:
    norm = file_path.replace("\\", "/")
    if "/src/bioetl/" in norm or norm.endswith("/src/bioetl"):
        return "src"
    if "/tests/" in norm:
        return "tests"
    if "/scripts/" in norm:
        return "scripts"
    if "/src/" in norm:
        return "src-other"
    return "other"


def _rel(file_path: str) -> str:
    norm = file_path.replace("\\", "/")
    for marker in ("/src/", "/tests/", "/scripts/"):
        idx = norm.find(marker)
        if idx != -1:
            return norm[idx + 1 :]
    return norm.rsplit("/", 1)[-1]


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def build_plan(diagnostics: list[dict[str, Any]], severity: str, top_files: int) -> dict[str, Any]:
    errors = [d for d in diagnostics if d.get("severity") == severity]

    rule_tree = Counter()
    rule_total = Counter()
    tree_total = Counter()
    rule_files: dict[str, Counter] = defaultdict(Counter)
    for d in errors:
        rule = d.get("rule") or "(no-rule)"
        tree = _tree_of(str(d.get("file", "")))
        rule_tree[(rule, tree)] += 1
        rule_total[rule] += 1
        tree_total[tree] += 1
        rule_files[rule][_rel(str(d.get("file", "")))] += 1

    clusters: list[dict[str, Any]] = []
    for rule, total in sorted(rule_total.items(), key=lambda kv: (-kv[1], kv[0])):
        plan = RULE_PLAN.get(rule, _GENERIC_PLAN)
        by_tree = {
            tree: rule_tree[(rule, tree)]
            for tree in sorted(
                {t for (r, t) in rule_tree if r == rule},
                key=lambda t: (-rule_tree[(rule, t)], t),
            )
        }
        top = [
            {"file": f, "count": c}
            for f, c in sorted(rule_files[rule].items(), key=lambda kv: (-kv[1], kv[0]))[:top_files]
        ]
        clusters.append(
            {
                "rule": rule,
                "count": total,
                "rf": plan.rf,
                "default_severity": plan.default_severity,
                "by_tree": by_tree,
                "cause": plan.cause,
                "fix": plan.fix,
                "validation": plan.validation,
                "top_files": top,
            }
        )

    return {
        "severity": severity,
        "total": len(errors),
        "by_tree": dict(sorted(tree_total.items(), key=lambda kv: (-kv[1], kv[0]))),
        "clusters": clusters,
    }


def render_markdown(plan: dict[str, Any], label: str) -> str:
    lines: list[str] = []
    lines.append(f"# Project Diagnostics — {label} error plan (generated)")
    lines.append("")
    lines.append(
        f"Total `{plan['severity']}` diagnostics: **{plan['total']}** · "
        f"by tree: " + ", ".join(f"{t}={n}" for t, n in plan["by_tree"].items())
    )
    lines.append("")
    lines.append(
        "Priority order: **src (product, invariant errors=0) > tests > scripts**. "
        "Every removal of a suppression requires a structural fix in the same PR; "
        "never raise a debt budget (AGENTS.md)."
    )
    lines.append("")
    lines.append("| rule | count | by tree | RF | fix recipe |")
    lines.append("| --- | ---: | --- | --- | --- |")
    for c in plan["clusters"]:
        by_tree = " ".join(f"{t}:{n}" for t, n in c["by_tree"].items())
        lines.append(
            f"| `{c['rule']}` | {c['count']} | {by_tree} | {c['rf']} | {c['fix']} |"
        )
    lines.append("")
    lines.append("## Top files per rule")
    lines.append("")
    for c in plan["clusters"]:
        lines.append(f"### `{c['rule']}` ({c['count']}) → {c['rf']}")
        lines.append(f"- cause: {c['cause']}")
        lines.append(f"- validation: {c['validation']}")
        for tf in c["top_files"]:
            lines.append(f"  - {tf['file']} — {tf['count']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--label", default="workspace")
    parser.add_argument("--severity", default="error")
    parser.add_argument("--top-files", type=int, default=15)
    args = parser.parse_args(argv)

    if not args.source.exists():
        parser.error(
            f"basedpyright json not found: {args.source}. Run "
            f"`basedpyright --outputjson > {args.source}` first."
        )

    data = json.loads(args.source.read_text(encoding="utf-8"))
    diagnostics = data.get("generalDiagnostics", [])
    plan = build_plan(diagnostics, args.severity, args.top_files)
    plan["label"] = args.label
    plan["source"] = str(args.source).replace("\\", "/")
    if isinstance(data.get("summary"), dict):
        plan["basedpyright_summary"] = data["summary"]

    _atomic_write(args.out_json, json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=False) + "\n")
    _atomic_write(args.out_md, render_markdown(plan, args.label))

    print(
        f"[{args.label}] {plan['total']} {args.severity} diagnostics across "
        f"{len(plan['clusters'])} rule clusters -> {args.out_md}"
    )
    for c in plan["clusters"][:12]:
        print(f"  {c['count']:>6}  {c['rule']:<40} {c['rf']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
