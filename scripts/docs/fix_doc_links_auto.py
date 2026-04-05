import os
import re
from pathlib import Path

DOCS_DIR = Path("docs")
PROJECT_ROOT = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2")

RULES_OLD = "docs/RULES.md"
RULES_NEW = "docs/00-project/RULES.md"


def fix_links():
    md_files = list(DOCS_DIR.rglob("*.md"))
    fixed_count = 0

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        original_content = content

        # 1. Fix absolute-looking links like [text](docs/...) to be relative
        # Example: from docs/00-project/ai/agents/AGENT.md, [ADR-007](docs/02-architecture/decisions/...)
        # should be [ADR-007](../../02-architecture/decisions/...)

        def rel_fix(match):
            text = match.group(1)
            raw_target = match.group(2)

            if raw_target.startswith("docs/"):
                # Calculate relative path from md_file to DOCS_DIR
                depth = len(md_file.relative_to(DOCS_DIR).parent.parts)
                rel_prefix = "../" * depth
                new_target = rel_prefix + raw_target[5:]
                return f"[{text}]({new_target})"
            return match.group(0)

        content = re.sub(r"\[([^\]]*)\]\((docs/[^)# ]+)\)", rel_fix, content)

        # 2. Fix RULES.md specifically if it's still wrong
        # If it points to ../RULES.md from docs/02-architecture/ it should be ../00-project/RULES.md
        # My previous PowerShell fix might have missed some or done it wrong.

        # 3. Fix Mermaid links
        # [Five Layer Architecture](diagrams/mermaid/01_five_layer_architecture.mmd)
        # to [Five Layer Architecture](diagrams/mermaid/01-high-level.mermaid) or similar
        # This is harder because filenames changed significantly.
        # I'll just fix the directory and extension for now if they match patterns.

        content = content.replace(".mmd", ".mermaid")
        content = content.replace("_", "-")  # Dangerous? Only inside links?

        # Re-apply the underscore to dash only in filenames within links
        def dash_fix(match):
            return match.group(0).replace("_", "-")

        content = re.sub(r"\]\([^)]+\.mermaid\)", dash_fix, content)

        if content != original_content:
            md_file.write_text(content, encoding="utf-8")
            fixed_count += 1
            print(f"Fixed: {md_file}")

    print(f"Total files fixed: {fixed_count}")


if __name__ == "__main__":
    fix_links()
