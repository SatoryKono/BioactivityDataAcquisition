"""Fix common Mermaid diagram syntax issues."""

from __future__ import annotations

import re
from pathlib import Path


def fix_mermaid_file(file_path: Path) -> tuple[bool, list[str]]:
    """Fix common issues in Mermaid diagram file.
    
    Returns:
        Tuple of (was_modified, list_of_changes)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        original = content
        changes = []
        
        # Remove semicolons at end of classDef lines
        pattern1 = r"(classDef\s+[^\n]+);(\s*)$"
        if re.search(pattern1, content, re.MULTILINE):
            content = re.sub(pattern1, r"\1\2", content, flags=re.MULTILINE)
            if content != original:
                changes.append("Removed semicolons from classDef")
                original = content
        
        # Remove semicolons at end of linkStyle lines
        pattern2 = r"(linkStyle\s+[^\n]+);(\s*)$"
        if re.search(pattern2, content, re.MULTILINE):
            content = re.sub(pattern2, r"\1\2", content, flags=re.MULTILINE)
            if content != original:
                changes.append("Removed semicolons from linkStyle")
                original = content
        
        # Fix classDef with semicolon before newline (not at end of line)
        pattern3 = r"(classDef\s+[^;]+);(\n)"
        if re.search(pattern3, content):
            content = re.sub(pattern3, r"\1\2", content)
            if content != original:
                changes.append("Removed semicolons from classDef (inline)")
                original = content
        
        # Fix linkStyle with semicolon before newline
        pattern4 = r"(linkStyle\s+[^;]+);(\n)"
        if re.search(pattern4, content):
            content = re.sub(pattern4, r"\1\2", content)
            if content != original:
                changes.append("Removed semicolons from linkStyle (inline)")
        
        if changes:
            file_path.write_text(content, encoding="utf-8")
            return True, changes
        
        return False, []
    
    except Exception as e:
        return False, [f"Error: {e}"]


def main() -> None:
    """Fix all Mermaid diagrams in the project."""
    docs_dir = Path("docs")
    mmd_files = list(docs_dir.rglob("*.mmd"))
    
    print(f"Found {len(mmd_files)} Mermaid diagram files")
    
    modified_count = 0
    total_changes = []
    
    for mmd_file in sorted(mmd_files):
        was_modified, changes = fix_mermaid_file(mmd_file)
        if was_modified:
            modified_count += 1
            rel_path = str(mmd_file).replace(str(Path.cwd()) + "\\", "").replace("\\", "/")
            print(f"✓ {rel_path}: {', '.join(changes)}")
            total_changes.extend(changes)
    
    print(f"\nModified {modified_count} out of {len(mmd_files)} files")


if __name__ == "__main__":
    main()

