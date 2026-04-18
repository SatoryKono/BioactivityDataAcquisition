#!/usr/bin/env python3
"""
Migration script to help update deprecated class names in the codebase.

This script helps identify and optionally replace deprecated class names
with their new equivalents.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping of deprecated names to new names
DEPRECATED_MAPPING = {
    "CheckpointManager": "CheckpointManagerService",
    "CompositeCheckpointManager": "CompositeCheckpointService",
    "CompositePreflightValidator": "CompositePreflightValidationService",
    "CompositePipelineRunnerService": "CompositePipelineRunner",  # Reverse mapping
    "EnricherDeduplicator": "EnricherDeduplicatorService",
    "FSMStateHelper": "FSMStateHelperService",
    "BatchMetricsRecorder": "BatchMetricsRecorderService",
    "DataSourceCreatorPort": "DataSourceCreatorProtocol",
}

def find_deprecated_usage(root_dir: Path, pattern: str = "**.py") -> dict[str, list[tuple[int, str]]]:
    """Find all usages of deprecated class names in Python files."""

    results = {}

    for py_file in root_dir.rglob(pattern):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            found_uses = []
            for line_num, line in enumerate(lines, 1):
                for deprecated_name in DEPRECATED_MAPPING:
                    # Look for import statements or instantiations
                    if re.search(rf'\b{deprecated_name}\b', line):
                        found_uses.append((line_num, line.strip()))
                        break

            if found_uses:
                results[str(py_file)] = found_uses
        except (UnicodeDecodeError, PermissionError):
            continue

    return results

def main():
    """Main function to find and report deprecated class usage."""

    if len(sys.argv) < 2:
        print("Usage: python migrate_deprecated_names.py <directory> [--dry-run]")
        print("Example: python migrate_deprecated_names.py src/")
        sys.exit(1)

    root_dir = Path(sys.argv[1])
    if not root_dir.exists():
        print(f"Error: Directory {root_dir} does not exist")
        sys.exit(1)

    dry_run = "--dry-run" in sys.argv

    print("Searching for deprecated class usage...")
    results = find_deprecated_usage(root_dir)

    if not results:
        print("No deprecated class usage found!")
        return

    print(f"Found {len(results)} files with deprecated class usage:\n")

    for file_path, uses in results.items():
        print(f"File: {file_path}")
        for line_num, line in uses:
            print(f"  {line_num:4d}: {line}")
        print()

    print(f"\nSummary: {len(results)} files need updating")

    if dry_run:
        print("\nDry run complete. No files were modified.")
        print("Run without --dry-run to see replacement suggestions.")
    else:
        print("\nTo update these files:")
        print("1. Review the changes above")
        print("2. Manually update each file using the mapping:")
        for old, new in DEPRECATED_MAPPING.items():
            print(f"   - Replace '{old}' with '{new}'")

if __name__ == "__main__":
    main()
