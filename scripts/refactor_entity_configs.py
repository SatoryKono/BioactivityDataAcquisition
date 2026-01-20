#!/usr/bin/env python3
"""Refactor entity configs by removing duplicates from _base.yaml.

Usage: python scripts/refactor_entity_configs.py [--dry-run]

Creates backup of original configs in configs/pipelines/.backup/
"""

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path


def remove_ascending_true(content: str) -> str:
    """Remove 'ascending: true' lines from sort_by sections."""
    # Pattern to match '      ascending: true' with proper indentation
    # This removes the line completely
    pattern = r'\n\s+ascending:\s*true\s*(?=\n)'
    return re.sub(pattern, '', content)


def remove_empty_partition_by(content: str) -> str:
    """Remove 'partition_by: []' lines when it's the default."""
    # Pattern to match 'partition_by: []' with proper indentation
    # Only remove if it's an empty list
    pattern = r'\n\s+partition_by:\s*\[\]\s*(?=\n)'
    return re.sub(pattern, '', content)


def remove_schema_version(content: str) -> str:
    """Remove schema_version from entity configs (inherited from _base.yaml)."""
    # Pattern to match 'schema_version: "2.0.0"' line
    pattern = r'\nschema_version:\s*["\']?[\d.]+["\']?\s*(?=\n)'
    return re.sub(pattern, '', content)


def remove_source_load_strategy_full(content: str) -> str:
    """Remove 'source.load_strategy: full' if it matches default."""
    # Only for configs that have this as standalone
    # Pattern for source section with only load_strategy: full
    pattern = r'\nsource:\s*\n\s+load_strategy:\s*full\s*(?=\n\n)'
    return re.sub(pattern, '', content)


def remove_maintenance_defaults(content: str) -> str:
    """Remove maintenance section if it only has default values."""
    # Pattern for maintenance section with default values only
    pattern = r'\n# -{79}\n# Maintenance Configuration\n# -{79}\nmaintenance:\s*\n\s+auto_vacuum:\s*true\s*\n\s+vacuum_retention_days:\s*7\s*\n'
    result = re.sub(pattern, '', content)

    # Simpler pattern for just the section
    pattern2 = r'\nmaintenance:\s*\n\s+auto_vacuum:\s*true\s*\n\s+vacuum_retention_days:\s*7\s*\n?$'
    return re.sub(pattern2, '\n', result)


def remove_dq_report_disabled(content: str) -> str:
    """Remove verbose dq_report sections when enabled: false."""
    # Pattern to match dq_report sections that are disabled
    # This is a multi-line pattern
    pattern = r'(\n\s+# DQ report configuration.*?\n\s+dq_report:\s*\n\s+enabled:\s*false.*?)(?=\n\s+(?:silver|gold|#|$|\w+:))'

    # Use DOTALL to match across lines
    result = re.sub(pattern, '', content, flags=re.DOTALL)
    return result


def cleanup_extra_blank_lines(content: str) -> str:
    """Remove more than 2 consecutive blank lines."""
    return re.sub(r'\n{3,}', '\n\n', content)


def process_file(config_path: Path, dry_run: bool) -> tuple[int, int]:
    """Process a single config file.

    Returns:
        Tuple of (original_lines, new_lines)
    """
    original_content = config_path.read_text(encoding='utf-8')
    original_lines = original_content.count('\n')

    # Apply transformations
    content = original_content
    content = remove_ascending_true(content)
    content = remove_empty_partition_by(content)
    content = remove_schema_version(content)
    content = remove_source_load_strategy_full(content)
    content = remove_maintenance_defaults(content)
    content = remove_dq_report_disabled(content)
    content = cleanup_extra_blank_lines(content)

    # Ensure file ends with single newline
    content = content.rstrip() + '\n'

    new_lines = content.count('\n')

    if not dry_run and content != original_content:
        config_path.write_text(content, encoding='utf-8')

    return original_lines, new_lines


def main():
    parser = argparse.ArgumentParser(description="Refactor entity configs")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    configs_root = Path("configs/pipelines")
    backup_dir = configs_root / ".backup" / datetime.now().strftime("%Y%m%d_%H%M%S")

    if not args.dry_run:
        # Create backup
        backup_dir.mkdir(parents=True, exist_ok=True)

    stats = {"processed": 0, "modified": 0, "lines_removed": 0}

    for provider_dir in sorted(configs_root.iterdir()):
        if not provider_dir.is_dir() or provider_dir.name.startswith(("_", ".")):
            continue

        for config_file in sorted(provider_dir.glob("*.yaml")):
            stats["processed"] += 1

            # Backup original
            if not args.dry_run:
                backup_path = backup_dir / provider_dir.name / config_file.name
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_file, backup_path)

            original_lines, new_lines = process_file(config_file, args.dry_run)

            diff = original_lines - new_lines
            if diff > 0:
                stats["modified"] += 1
                stats["lines_removed"] += diff
                action = "[DRY-RUN]" if args.dry_run else "✓"
                print(f"{action} {config_file.name}: {original_lines} → {new_lines} lines (-{diff})")
            elif diff < 0:
                print(f"! {config_file.name}: {original_lines} → {new_lines} lines (+{-diff})")

    print(f"\n{'=' * 60}")
    print(f"SUMMARY {'(DRY RUN)' if args.dry_run else ''}")
    print(f"{'=' * 60}")
    print(f"Processed: {stats['processed']} configs")
    print(f"Modified: {stats['modified']} configs")
    print(f"Lines removed: {stats['lines_removed']}")
    if not args.dry_run and stats['modified'] > 0:
        print(f"Backups saved to: {backup_dir}")

    return 0


if __name__ == "__main__":
    exit(main())
