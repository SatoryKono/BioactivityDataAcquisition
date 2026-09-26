#!/usr/bin/env python3
"""Count lines in Python source files to find largest modules."""

from pathlib import Path


def count_lines(filepath: Path) -> int:
    """Count non-empty, non-comment lines in a Python file."""
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        # Count all lines (including comments and blanks) for governance inventory
        return len(lines)
    except Exception:
        return 0


def main():
    src_root = Path("src/bioetl")
    py_files = list(src_root.rglob("*.py"))

    file_counts = []
    for py_file in py_files:
        if py_file.name == "__init__.py":
            continue
        line_count = count_lines(py_file)
        if line_count > 50:  # Only track files with significant content
            file_counts.append((py_file, line_count))

    # Sort by line count descending
    file_counts.sort(key=lambda x: x[1], reverse=True)

    print(f"Total Python files: {len(py_files)}")
    print(f"Files with >50 lines: {len(file_counts)}")
    print("\nTop 70 largest files:")
    for i, (filepath, count) in enumerate(file_counts[:70], 1):
        rel_path = filepath.relative_to(Path.cwd())
        print(f"{i:3d}. {count:4d} lines: {rel_path}")


if __name__ == "__main__":
    main()
