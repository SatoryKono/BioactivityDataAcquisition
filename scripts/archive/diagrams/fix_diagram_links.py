
import os
import re
from pathlib import Path

DOCS_DIR = Path("docs")

def fix_links():
    md_files = list(DOCS_DIR.rglob("*.md"))
    fixed_count = 0

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        original_content = content

        # 1. Remove 'mermaid/' from diagram paths
        # [Text](diagrams/mermaid/file.mermaid) -> [Text](diagrams/file.mermaid)
        content = content.replace("diagrams/mermaid/", "diagrams/")

        # 2. Fix .mmd extension to .mermaid
        content = content.replace(".mmd", ".mermaid")

        # 3. Fix common diagram names that use underscores but should use dashes
        # This is tricky, I'll only do it for known diagrams if they are still failing.
        # Let's try to find all links to .mermaid files and normalize them.

        def mermaid_link_fix(match):
            link_text = match.group(1)
            path = match.group(2)
            # Normalize path: underscores to dashes in the filename part
            parts = path.split("/")
            filename = parts[-1]
            if ".mermaid" in filename:
                filename = filename.replace("_", "-")
            elif "v1.0.json" in filename:
                filename = filename.replace("-", "_")
            new_path = "/".join(parts[:-1] + [filename])
            return f"[{link_text}]({new_path})"

        content = re.sub(r"\[([^\]]*)\]\(([^)]+(?:\.mermaid|v1\.0\.json))\)", mermaid_link_fix, content)

        if content != original_content:
            md_file.write_text(content, encoding="utf-8")
            fixed_count += 1
            print(f"Fixed: {md_file}")

    print(f"Total files fixed: {fixed_count}")

if __name__ == "__main__":
    fix_links()
