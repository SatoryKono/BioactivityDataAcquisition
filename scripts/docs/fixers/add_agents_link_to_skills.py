#!/usr/bin/env python3
"""Add AGENTS.md link to all local skill SKILL.md files."""

from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SKILLS_DIR = PROJECT_ROOT / "docs/00-project/ai/skills/local"

SKILL_FILES = list(SKILLS_DIR.rglob("*/SKILL.md"))

for skill_file in SKILL_FILES:
    content = skill_file.read_text(encoding="utf-8")
    
    # Check if AGENTS.md is already referenced
    if "AGENTS.md" in content:
        print(f"Skipping {skill_file.relative_to(PROJECT_ROOT)} - already has AGENTS.md")
        continue
    
    # Find the position to insert (after the first header or at the beginning)
    lines = content.splitlines()
    
    # Find the first line that starts with ## or after the first line
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith("##"):
            insert_pos = i
            break
    
    # Insert AGENTS.md reference
    # Calculate relative path from skill file to AGENTS.md
    relative_path = Path(os.path.relpath(PROJECT_ROOT / "AGENTS.md", start=skill_file.parent))
    relative_path_str = relative_path.as_posix()
    
    # Insert after the first line or at the beginning
    if insert_pos == 0:
        # No ## header found, insert at the beginning
        lines.insert(0, f"- `{relative_path_str}`")
        lines.insert(0, "## Canonical Sources")
        lines.insert(0, "")
        lines.insert(0, "Read before planning or editing:")
    else:
        # Insert after the header
        lines.insert(insert_pos + 1, f"- `{relative_path_str}`")
    
    skill_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Updated {skill_file.relative_to(PROJECT_ROOT)}")

print(f"Updated {len(SKILL_FILES)} skill files")
