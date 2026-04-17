#!/usr/bin/env python3
"""Auto-fix documentation link targets after bulk docs restructuring."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from scripts.docs.common.paths import DOCS_DIR


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Auto-fix documentation links inside the docs tree."
    )


def fix_links() -> None:
    md_files = list(DOCS_DIR.rglob("*.md"))
    fixed_count = 0

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        original_content = content

        def rel_fix(match: re.Match[str], current_md_file: Path = md_file) -> str:
            text = match.group(1)
            raw_target = match.group(2)

            if raw_target.startswith("docs/"):
                depth = len(current_md_file.relative_to(DOCS_DIR).parent.parts)
                rel_prefix = "../" * depth
                new_target = rel_prefix + raw_target[5:]
                return f"[{text}]({new_target})"
            return match.group(0)

        content = re.sub(r"\[([^\]]*)\]\((docs/[^)# ]+)\)", rel_fix, content)

        content = content.replace(".mmd", ".mermaid")
        content = content.replace("_", "-")

        def dash_fix(match: re.Match[str]) -> str:
            return match.group(0).replace("_", "-")

        content = re.sub(r"\]\([^)]+\.mermaid\)", dash_fix, content)

        if content != original_content:
            md_file.write_text(content, encoding="utf-8")
            fixed_count += 1
            print(f"Fixed: {md_file}")

    print(f"Total files fixed: {fixed_count}")


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    fix_links()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
