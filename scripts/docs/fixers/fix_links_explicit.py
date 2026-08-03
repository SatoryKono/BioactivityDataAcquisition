#!/usr/bin/env python3
"""Apply explicit link rewrite rules inside the docs tree."""

from __future__ import annotations

import argparse

from scripts.docs.common.paths import DOCS_DIR

FIX_MAP = {
    "../04-reference/contracts/gold/chembl-activity-v1.0.json": "../04-reference/contracts/gold/chembl_activity_v1.0.json",
    "../../glossary.md": "../glossary.md",
    "../02-architecture/decisions/ADR-014-deterministic-writes.md": "../../02-architecture/decisions/ADR-014-deterministic-writes.md",
    "../02-architecture/decisions/ADR-025-pipeline-config-unification.md": "../../02-architecture/decisions/ADR-025-pipeline-config-unification.md",
    "../03-guides/add-new-source.md": "../../03-guides/add-new-source.md",
    "quick-reference/rules-summary.md": "rules-summary.md",
    "03-guides/quick-start.md": "../03-guides/quick-start.md",
    "02-architecture/system-context.md": "../02-architecture/system-context.md",
    "03-guides/": "../03-guides/",
}


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Apply explicit documentation link rewrites inside the docs tree."
    )


def fix_all_broken_links() -> None:
    md_files = list(DOCS_DIR.rglob("*.md"))
    fixed_count = 0

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        original_content = content

        for old, new in FIX_MAP.items():
            content = content.replace(f"({old})", f"({new})")

        if (
            "02-architecture" in str(md_file)
            and md_file.parent.name == "02-architecture"
        ):
            content = content.replace("](../RULES.md)", "](../00-project/RULES.md)")

        if content != original_content:
            md_file.write_text(content, encoding="utf-8")
            fixed_count += 1
            print(f"Explicitly fixed: {md_file}")

    print(f"Total files explicitly fixed: {fixed_count}")


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    fix_all_broken_links()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
