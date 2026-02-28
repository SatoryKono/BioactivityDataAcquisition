"""Fix diagram links in documentation markdown files.

Normalizes diagram link paths: removes legacy 'mermaid/' subdirectory,
converts .mmd extensions to .mermaid within markdown link syntax only,
and normalizes filenames to kebab-case.
"""

import re
import sys
from pathlib import Path

DOCS_DIR = Path("docs")

# Only match .mmd when it appears as a file extension inside a markdown link
_LINK_MMD_RE = re.compile(r"(\[[^\]]*\]\([^)]+)\.mmd(\))")


def fix_links() -> int:
    """Fix diagram links in all markdown files. Returns count of fixed files."""
    md_files = list(DOCS_DIR.rglob("*.md"))
    fixed_count = 0

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        original_content = content

        # 1. Remove 'mermaid/' from diagram paths (in links only)
        content = content.replace("diagrams/mermaid/", "diagrams/")

        # 2. Fix .mmd extension to .mermaid ONLY inside markdown links
        content = _LINK_MMD_RE.sub(r"\1.mermaid\2", content)

        # 3. Normalize filenames in diagram links
        def mermaid_link_fix(match: re.Match[str]) -> str:
            link_text = match.group(1)
            path = match.group(2)
            parts = path.split("/")
            filename = parts[-1]
            if ".mermaid" in filename:
                filename = filename.replace("_", "-")
            elif "v1.0.json" in filename:
                filename = filename.replace("-", "_")
            new_path = "/".join(parts[:-1] + [filename])
            return f"[{link_text}]({new_path})"

        content = re.sub(
            r"\[([^\]]*)\]\(([^)]+(?:\.mermaid|v1\.0\.json))\)",
            mermaid_link_fix,
            content,
        )

        if content != original_content:
            md_file.write_text(content, encoding="utf-8")
            fixed_count += 1
            print(f"Fixed: {md_file}")

    print(f"Total files fixed: {fixed_count}")
    return fixed_count


if __name__ == "__main__":
    sys.exit(0 if fix_links() >= 0 else 1)
