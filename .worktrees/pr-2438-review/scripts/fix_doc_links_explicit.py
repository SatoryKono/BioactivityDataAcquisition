
import re
from pathlib import Path

DOCS_DIR = Path("docs")

# Mapping of incorrect paths to correct ones
FIX_MAP = {
    "../04-reference/contracts/gold/chembl-activity-v1.0.json": "../04-reference/contracts/gold/chembl_activity_v1.0.json",
    "../../glossary.md": "../glossary.md", # For files in governance/
    "../02-architecture/decisions/ADR-014-deterministic-writes.md": "../../02-architecture/decisions/ADR-014-deterministic-writes.md", # For files in governance/
    "../02-architecture/decisions/ADR-025-pipeline-config-unification.md": "../../02-architecture/decisions/ADR-025-pipeline-config-unification.md", # For files in governance/
    "../03-guides/add-new-source.md": "../../03-guides/add-new-source.md", # For files in governance/
    "quick-reference/rules-summary.md": "rules-summary.md", # For index.md in 00-project
    "03-guides/quick-start.md": "../03-guides/quick-start.md", # For index.md in 00-project
    "02-architecture/system-context.md": "../02-architecture/system-context.md", # For index.md in 00-project
    "03-guides/": "../03-guides/", # For index.md in 00-project
}

def fix_all_broken_links():
    md_files = list(DOCS_DIR.rglob("*.md"))
    fixed_count = 0
    
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        original_content = content
        
        # Apply explicit map
        for old, new in FIX_MAP.items():
            content = content.replace(f"({old})", f"({new})")
            
        # Fix Mermaid links starting with diagrams/ but missing ../
        if "02-architecture" in str(md_file):
            # From docs/02-architecture/*.md, diagrams/ should be just diagrams/
            # But from subfolders it might be different.
            pass
            
        # Fix ../RULES.md from 02-architecture
        if "02-architecture" in str(md_file) and md_file.parent.name == "02-architecture":
             content = content.replace("](../RULES.md)", "](../00-project/RULES.md)")

        if content != original_content:
            md_file.write_text(content, encoding="utf-8")
            fixed_count += 1
            print(f"Explicitly fixed: {md_file}")

    print(f"Total files explicitly fixed: {fixed_count}")

if __name__ == "__main__":
    fix_all_broken_links()
