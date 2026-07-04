#!/usr/bin/env python3
"""Add required policy links to all SKILL.md files."""

import os
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

SKILL_DIRS = [
    PROJECT_ROOT / ".codex/skills",
    PROJECT_ROOT / ".devin/skills",
    PROJECT_ROOT / "docs/00-project/ai/skills/local",
]

# Required links for runtime skills (.codex, .devin)
RUNTIME_REQUIRED_LINKS = [
    ("AGENTS.md", "Root runtime contract"),
    ("docs/00-project/RULES.md", "Project rules"),
    ("docs/01-requirements/REQUIREMENTS.md", "Requirements"),
    ("docs/02-architecture/decisions", "Accepted ADRs"),
]

# Required links for docs mirror skills (docs/00-project/ai/skills/local)
DOCS_MIRROR_REQUIRED_LINKS = [
    ("NORMATIVE_SOURCES.md", "Normative index"),
    ("AGENTS.md", "Root runtime contract"),
    ("RULES.md", "Project rules"),
    ("01-requirements/REQUIREMENTS.md", "Requirements"),
    ("02-architecture/decisions", "Accepted ADRs"),
]


def calculate_relative_path(from_dir: Path, target: Path) -> str:
    """Calculate relative path from from_dir to target."""
    return os.path.relpath(str(target), str(from_dir))


def add_links_to_skill_file(skill_file: Path, required_links: list[tuple[str, str]]) -> bool:
    """Add required links to a SKILL.md file if missing."""
    content = skill_file.read_text(encoding="utf-8")
    original_content = content

    # Find or create "Source Of Truth" section
    source_section_pattern = r"(## Source Of Truth\n|## Source of Truth\n)"
    source_section_match = re.search(source_section_pattern, content, re.IGNORECASE)

    if not source_section_match:
        # Add Source Of Truth section after Objective section or at the end
        objective_pattern = r"(## Objective\n.*?)(\n##|\Z)"
        objective_match = re.search(objective_pattern, content, re.DOTALL)

        if objective_match:
            insert_pos = objective_match.end(1)
            new_section = "\n## Source Of Truth\n\n"
            content = content[:insert_pos] + new_section + content[insert_pos:]
        else:
            # Add at the end
            content += "\n## Source Of Truth\n\n"

    # Recalculate source_section_pattern after potential addition
    source_section_match = re.search(r"(## Source Of Truth\n|## Source of Truth\n)", content, re.IGNORECASE)

    if source_section_match:
        section_start = source_section_match.end()
        # Find the end of the section (next ## or end of file)
        next_section_match = re.search(r"\n## ", content[section_start:])
        if next_section_match:
            section_end = section_start + next_section_match.start()
        else:
            section_end = len(content)

        section_content = content[section_start:section_end]

        # Calculate relative paths
        skill_dir = skill_file.parent
        is_docs_mirror = "docs/00-project/ai/skills/local" in str(skill_file)

        for link_name, description in required_links:
            # Determine target path
            if is_docs_mirror:
                if link_name == "NORMATIVE_SOURCES.md":
                    target = PROJECT_ROOT / "docs/00-project" / link_name
                elif link_name == "AGENTS.md":
                    target = PROJECT_ROOT / link_name
                elif link_name == "RULES.md":
                    target = PROJECT_ROOT / "docs/00-project" / link_name
                elif link_name.startswith("01-"):
                    target = PROJECT_ROOT / "docs" / link_name
                elif link_name.startswith("02-"):
                    target = PROJECT_ROOT / "docs" / link_name
                else:
                    target = PROJECT_ROOT / link_name
            else:
                if link_name == "AGENTS.md":
                    target = PROJECT_ROOT / link_name
                elif link_name.startswith("docs/"):
                    target = PROJECT_ROOT / link_name
                else:
                    target = PROJECT_ROOT / link_name

            rel_path = calculate_relative_path(skill_dir, target)

            # Check if link already exists (by exact path)
            link_exists = False
            for line in section_content.split('\n'):
                if rel_path in line:
                    link_exists = True
                    break

            # If link doesn't exist with correct path, check if it exists with wrong path
            if not link_exists:
                for line in section_content.split('\n'):
                    if link_name in line:
                        # Replace the line with correct path
                        new_line = f"- {description}: `{rel_path}`"
                        content = content.replace(line, new_line)
                        link_exists = True
                        break

            if not link_exists:
                # Add the link
                new_link = f"- {description}: `{rel_path}`\n"
                content = content[:section_end] + new_link + content[section_end:]
                section_end += len(new_link)

    if content != original_content:
        skill_file.write_text(content, encoding="utf-8")
        print(f"  Updated: {skill_file.relative_to(PROJECT_ROOT)}")
        return True
    return False


def main():
    updated_count = 0

    for skill_dir in SKILL_DIRS:
        if not skill_dir.exists():
            continue

        print(f"Processing: {skill_dir.relative_to(PROJECT_ROOT)}")
        for skill_file in sorted(skill_dir.rglob("SKILL.md")):
            is_docs_mirror = "docs/00-project/ai/skills/local" in str(skill_file)
            required_links = DOCS_MIRROR_REQUIRED_LINKS if is_docs_mirror else RUNTIME_REQUIRED_LINKS

            if add_links_to_skill_file(skill_file, required_links):
                updated_count += 1

    print(f"\nTotal updated: {updated_count}")


if __name__ == "__main__":
    main()
