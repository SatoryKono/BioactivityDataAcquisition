#!/usr/bin/env python3
"""Get largest Python modules by line count."""

import os
from pathlib import Path

def get_line_count(filepath):
    """Get line count for a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except (OSError, UnicodeDecodeError):
        return 0

def main():
    src_root = Path("src/bioetl")
    results = []

    for root, dirs, files in os.walk(src_root):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = Path(root) / file
                line_count = get_line_count(filepath)
                if line_count > 50:
                    rel_path = filepath.relative_to(Path.cwd())
                    results.append((rel_path, line_count))

    results.sort(key=lambda x: x[1], reverse=True)

    print(f"Found {len(results)} files with >50 lines")
    print("\nTop 70 largest modules:")
    for i, (path, count) in enumerate(results[:70], 1):
        print(f"{i:3d}. {count:4d} lines: {path}")

if __name__ == "__main__":
    main()

