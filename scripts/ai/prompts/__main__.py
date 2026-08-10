#!/usr/bin/env python3
"""CLI for BioETL Prompt Library (epic #8513).

Usage:
  python -m scripts.ai.prompts list
  python -m scripts.ai.prompts show prompt.audit.grok-cycle
  python -m scripts.ai.prompts render prompt.audit.grok-cycle --param SCOPE=src/bioetl/domain
  python -m scripts.ai.prompts check-registry
  python -m scripts.ai.prompts check
  python -m scripts.ai.prompts catalog
  python -m scripts.ai.prompts new --id prompt.example.demo --class operator-paste
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.ai.prompts.check import (
    check_hygiene,
    check_registry,
    format_report,
    write_quality_artifact,
)
from scripts.ai.prompts.registry import PROMPTS_ROOT, REPO_ROOT
from scripts.ai.prompts.render import (
    generate_catalog_markdown,
    list_entries,
    render_by_id,
    show_entry,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_CHECK = 1


def _parse_params(raw: list[str] | None) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in raw or []:
        if "=" not in item:
            raise SystemExit(f"--param must be KEY=VALUE, got: {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(f"empty param key in: {item!r}")
        params[key] = value
    return params


def cmd_list(args: argparse.Namespace) -> int:
    entries = list_entries(
        class_filter=args.class_filter,
        status_filter=None if args.all else (args.status or "active"),
    )
    if not entries:
        print("(no entries)")
        return EXIT_OK
    for entry in entries:
        summary = f" — {entry.summary}" if entry.summary else ""
        print(f"{entry.id}\t{entry.class_}\t{entry.status}\t{entry.path}{summary}")
    return EXIT_OK


def cmd_show(args: argparse.Namespace) -> int:
    try:
        sys.stdout.write(show_entry(args.id))
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    return EXIT_OK


def cmd_render(args: argparse.Namespace) -> int:
    try:
        params = _parse_params(args.param)
        text = render_by_id(args.id, params=params or None)
    except (KeyError, ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE if isinstance(exc, KeyError) else EXIT_CHECK
    if args.output:
        out = Path(args.output)
        if not out.is_absolute():
            out = REPO_ROOT / out
        # confine optional writes under reports/
        try:
            out.resolve().relative_to((REPO_ROOT / "reports").resolve())
        except ValueError:
            print(
                "refusing to write outside reports/: use --output reports/...",
                file=sys.stderr,
            )
            return EXIT_USAGE
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out.relative_to(REPO_ROOT)}", file=sys.stderr)
    sys.stdout.write(text)
    return EXIT_OK


def cmd_check_registry(args: argparse.Namespace) -> int:
    report = check_registry()
    sys.stdout.write(format_report(report, title="Prompt Library check-registry"))
    if args.artifact:
        write_quality_artifact(report, REPO_ROOT / args.artifact)
    return EXIT_OK if report.ok else EXIT_CHECK


def cmd_check(args: argparse.Namespace) -> int:
    reg = check_registry()
    hyg = check_hygiene()
    # merge
    reg.errors.extend(hyg.errors)
    reg.warnings.extend(hyg.warnings)
    reg.stats = {
        "registry": reg.stats,
        "hygiene": hyg.stats,
        "errors": len(reg.errors),
        "warnings": len(reg.warnings),
    }
    sys.stdout.write(format_report(reg, title="Prompt Library check (registry + hygiene)"))
    artifact = args.artifact or "reports/quality/prompts/check.json"
    if args.write_artifact or args.artifact:
        write_quality_artifact(reg, REPO_ROOT / artifact)
        print(f"artifact: {artifact}", file=sys.stderr)
    return EXIT_OK if reg.ok else EXIT_CHECK


def cmd_catalog(args: argparse.Namespace) -> int:
    text = generate_catalog_markdown()
    out = Path(args.output) if args.output else PROMPTS_ROOT / "generated" / "CATALOG.md"
    if not out.is_absolute():
        out = REPO_ROOT / out if str(out).startswith("reports") else out
        if not out.is_absolute():
            # default under prompts root already absolute via PROMPTS_ROOT
            pass
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    if args.stdout:
        sys.stdout.write(text)
    return EXIT_OK


def cmd_new(args: argparse.Namespace) -> int:
    prompt_id = args.id
    class_ = args.class_filter or args.prompt_class or "operator-paste"
    # derive relative path
    parts = prompt_id.split(".")
    if len(parts) < 3 or parts[0] != "prompt":
        print("id must look like prompt.<family>.<name>", file=sys.stderr)
        return EXIT_USAGE
    family = parts[1]
    name = "-".join(parts[2:])
    if class_ == "fragment":
        rel = Path("fragments") / f"{name}.md"
    else:
        rel = Path("library") / family / f"{name}.md"
    target = PROMPTS_ROOT / rel
    if target.exists() and not args.force:
        print(f"already exists: {rel} (use --force)", file=sys.stderr)
        return EXIT_USAGE
    target.parent.mkdir(parents=True, exist_ok=True)
    includes = [
        "fragments/read-order.md",
        "fragments/git-safety.md",
        "fragments/debt-budget-ban.md",
        "fragments/env-guardrail.md",
        "fragments/evidence-contract.md",
        "fragments/language-ru.md",
    ]
    includes_yaml = "\n".join(f"  - {i}" for i in includes)
    body = f"""---
id: {prompt_id}
version: 0.1.0
status: draft
class: {class_}
owner: BioETL Team
runtimes: [any]
params: [SCOPE, LANGUAGE]
includes:
{includes_yaml}
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
anti_patterns: []
tags: []
summary: TODO
---

# {prompt_id}

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | TODO |
| `LANGUAGE` | `ru` |

## Body

TODO: paste-ready instructions. Link SSOT; do not dump RULES.
"""
    target.write_text(body, encoding="utf-8")
    print(f"created {rel.as_posix()}")
    print("Remember to add an entry to REGISTRY.yaml and run check-registry.")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.ai.prompts",
        description="BioETL Prompt Library: list/show/render/check operator paste templates",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List registry entries")
    p_list.add_argument("--class", dest="class_filter", default=None)
    p_list.add_argument("--status", default="active")
    p_list.add_argument("--all", action="store_true", help="Ignore status filter")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show metadata for one id")
    p_show.add_argument("id")
    p_show.set_defaults(func=cmd_show)

    p_render = sub.add_parser("render", help="Render paste-ready text")
    p_render.add_argument("id")
    p_render.add_argument(
        "--param",
        action="append",
        default=[],
        help="KEY=VALUE (repeatable); fills {{KEY}} tokens",
    )
    p_render.add_argument(
        "--output",
        default=None,
        help="Optional write path under reports/",
    )
    p_render.set_defaults(func=cmd_render)

    p_cr = sub.add_parser("check-registry", help="Validate REGISTRY paths and ids")
    p_cr.add_argument(
        "--artifact",
        default=None,
        help="Optional JSON path under reports/",
    )
    p_cr.set_defaults(func=cmd_check_registry)

    p_check = sub.add_parser("check", help="Registry + paste hygiene gates")
    p_check.add_argument(
        "--artifact",
        default=None,
        help="JSON artifact path (default reports/quality/prompts/check.json with --write-artifact)",
    )
    p_check.add_argument(
        "--write-artifact",
        action="store_true",
        help="Write reports/quality/prompts/check.json",
    )
    p_check.set_defaults(func=cmd_check)

    p_cat = sub.add_parser("catalog", help="Generate generated/CATALOG.md from REGISTRY")
    p_cat.add_argument(
        "--output",
        default=None,
        help="Output path (default: docs/.../prompts/generated/CATALOG.md)",
    )
    p_cat.add_argument("--stdout", action="store_true")
    p_cat.set_defaults(func=cmd_catalog)

    p_new = sub.add_parser("new", help="Scaffold a draft card")
    p_new.add_argument("--id", required=True)
    p_new.add_argument(
        "--class",
        dest="prompt_class",
        default="operator-paste",
        choices=["operator-paste", "campaign", "fragment"],
    )
    p_new.add_argument("--force", action="store_true")
    # avoid clash with list --class namespace if shared
    p_new.set_defaults(func=cmd_new, class_filter=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
