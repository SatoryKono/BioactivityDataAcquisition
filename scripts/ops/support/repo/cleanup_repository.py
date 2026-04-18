#!/usr/bin/env python3
"""Repository cleanup script for BioETL.

This script helps maintain repository hygiene by identifying and optionally removing
common temporary files, cache directories, and other artifacts that shouldn't be
committed to git.

Usage:
    # Dry run (show what would be cleaned)
    python scripts/ops/support/repo/cleanup_repository.py --dry-run
    
    # Actually clean
    python scripts/ops/support/repo/cleanup_repository.py
    
    # Clean specific categories
    python scripts/ops/support/repo/cleanup_repository.py --cache --temp
"""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class RepositoryCleaner:
    """Main cleanup class for repository hygiene."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.root_dir = Path.cwd()
        self.files_removed = 0
        self.size_freed = 0

    def _get_file_size(self, path: Path) -> int:
        """Get file size in bytes."""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return 0

    def _remove_path(self, path: Path) -> bool:
        """Remove file or directory."""
        if not path.exists():
            return False

        size = self._get_file_size(path)

        if self.dry_run:
            logger.info(f"[DRY RUN] Would remove: {path} ({size:,} bytes)")
            return False

        try:
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)

            self.files_removed += 1
            self.size_freed += size
            logger.info(f"Removed: {path} ({size:,} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to remove {path}: {e}")
            return False

    def clean_cache_directories(self) -> None:
        """Clean common cache directories."""
        cache_patterns = [
            ".python-user",
            ".codex_tmp",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        ]

        logger.info("Cleaning cache directories...")
        for pattern in cache_patterns:
            for path in self.root_dir.rglob(pattern):
                if path.is_dir():
                    self._remove_path(path)

    def clean_temporary_files(self) -> None:
        """Clean temporary files."""
        temp_patterns = [
            "*.pyc",
            "*.pyo",
            "*.tmp",
            "*.log",
            "test_*.js",
            "test_*.json",
        ]

        logger.info("Cleaning temporary files...")
        for pattern in temp_patterns:
            for path in self.root_dir.rglob(pattern):
                if path.is_file():
                    # Skip package.json and package-lock.json
                    if path.name in ["package.json", "package-lock.json"]:
                        continue
                    self._remove_path(path)

    def clean_root_directory(self) -> None:
        """Clean root directory of orphan files."""
        logger.info("Cleaning root directory...")
        root_files = [
            "test_*.py",  # Keep our test scripts
        ]

        for pattern in root_files:
            for path in self.root_dir.glob(pattern):
                # Skip our intentional test scripts
                if path.name.startswith("test_") and path.suffix == ".py":
                    continue
                self._remove_path(path)

    def run(self, cache: bool = True, temp: bool = True, root: bool = True) -> None:
        """Run cleanup operations."""
        logger.info(f"Starting repository cleanup (dry_run={self.dry_run})")

        if cache:
            self.clean_cache_directories()

        if temp:
            self.clean_temporary_files()

        if root:
            self.clean_root_directory()

        logger.info(f"Cleanup complete: {self.files_removed} files, {self.size_freed:,} bytes freed")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BioETL Repository Cleanup Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without actually deleting files"
    )

    parser.add_argument(
        "--no-cache",
        action="store_false",
        dest="cache",
        help="Skip cache directory cleanup"
    )

    parser.add_argument(
        "--no-temp",
        action="store_false",
        dest="temp",
        help="Skip temporary file cleanup"
    )

    parser.add_argument(
        "--no-root",
        action="store_false",
        dest="root",
        help="Skip root directory cleanup"
    )

    args = parser.parse_args()

    cleaner = RepositoryCleaner(dry_run=args.dry_run)
    cleaner.run(cache=args.cache, temp=args.temp, root=args.root)


if __name__ == "__main__":
    main()
