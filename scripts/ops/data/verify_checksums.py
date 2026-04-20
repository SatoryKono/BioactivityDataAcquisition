#!/usr/bin/env python3
"""
verify_checksums.py - Verify checksums of critical artifacts.

Verifies the integrity of critical BioETL artifacts after DR recovery
or deployment. Compares current checksums against a stored manifest
to detect corruption or unauthorized modifications.

Critical artifacts include:
- Pipeline configuration files
- Schema definitions
- Migration scripts
- Critical infrastructure code

Usage:
    # Verify all critical artifacts
    python src/tools/verify_checksums.py

    # Generate new checksum manifest
    python src/tools/verify_checksums.py --generate

    # Verify specific directory
    python src/tools/verify_checksums.py --path configs/

    # Output JSON format
    python src/tools/verify_checksums.py --json

References:
    - 05-cleanup-policy.md §5.2: DR verification
    - RULES.md §5.5: Disaster Recovery

Make target: make verify-checksums

Aligned with RULES.md v5.24 (2026-01-06)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Default manifest location
DEFAULT_MANIFEST = PROJECT_ROOT / "checksums.json"

# Critical artifact patterns to verify
CRITICAL_PATTERNS: list[tuple[str, str]] = [
    # Unified configuration artifacts
    ("configs/base/**/*.yaml", "config_base"),
    ("configs/providers/**/*.yaml", "provider_config"),
    ("configs/entities/**/*.yaml", "entity_config"),
    ("configs/composites/**/*.yaml", "composite_config"),
    ("configs/_schema/**/*.json", "config_schema"),
    # Schema definitions
    ("src/bioetl/domain/schemas/*.py", "domain_schema"),
    ("src/bioetl/infrastructure/schemas/*.py", "infra_schema"),
    # Core domain models
    ("src/bioetl/domain/ports/*.py", "domain_port"),
    ("src/bioetl/domain/types.py", "domain_type"),
    ("src/bioetl/domain/config.py", "domain_config"),
    # Composition root (DI)
    ("src/bioetl/composition/bootstrap.py", "composition"),
    ("src/bioetl/composition/factories/*.py", "factory"),
    # Security-critical
    ("src/bioetl/infrastructure/security/*.py", "security"),
    # CLI interface
    ("src/bioetl/interfaces/cli.py", "interface"),
]

# Directories to skip
SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class FileChecksum:
    """Checksum for a single file."""

    path: str
    sha256: str
    category: str
    size: int
    modified: str


@dataclass
class ChecksumManifest:
    """Manifest of file checksums."""

    version: str
    generated_at: str
    files: dict[str, FileChecksum] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "files": {
                path: {
                    "sha256": fc.sha256,
                    "category": fc.category,
                    "size": fc.size,
                    "modified": fc.modified,
                }
                for path, fc in self.files.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> ChecksumManifest:
        """Create from dictionary."""
        manifest = cls(
            version=data.get("version", "1.0"),
            generated_at=data.get("generated_at", ""),
        )
        for path, fc_data in data.get("files", {}).items():
            manifest.files[path] = FileChecksum(
                path=path,
                sha256=fc_data["sha256"],
                category=fc_data.get("category", "unknown"),
                size=fc_data.get("size", 0),
                modified=fc_data.get("modified", ""),
            )
        return manifest


@dataclass
class VerificationResult:
    """Result of verification for a single file."""

    path: str
    category: str
    status: str  # "ok", "modified", "missing", "new"
    expected_hash: str | None = None
    actual_hash: str | None = None
    size_change: int | None = None


@dataclass
class VerificationReport:
    """Overall verification report."""

    results: list[VerificationResult] = field(default_factory=list)
    manifest_version: str = ""
    manifest_date: str = ""

    @property
    def ok_count(self) -> int:
        """Number of files that passed verification."""
        return sum(1 for r in self.results if r.status == "ok")

    @property
    def modified_count(self) -> int:
        """Number of modified files."""
        return sum(1 for r in self.results if r.status == "modified")

    @property
    def missing_count(self) -> int:
        """Number of missing files."""
        return sum(1 for r in self.results if r.status == "missing")

    @property
    def new_count(self) -> int:
        """Number of new files (not in manifest)."""
        return sum(1 for r in self.results if r.status == "new")

    @property
    def passed(self) -> bool:
        """True if verification passed (no modifications or missing files)."""
        return self.modified_count == 0 and self.missing_count == 0


# =============================================================================
# Checksum Functions
# =============================================================================


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to file.

    Returns:
        Hex-encoded SHA256 hash.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False


def find_critical_files(root: Path) -> list[tuple[Path, str]]:
    """Find all critical files matching patterns.

    Args:
        root: Project root directory.

    Returns:
        List of (path, category) tuples.
    """
    files = []

    for pattern, category in CRITICAL_PATTERNS:
        for file_path in root.glob(pattern):
            if file_path.is_file() and not _should_skip(file_path):
                files.append((file_path, category))

    return sorted(files, key=lambda x: str(x[0]))


def generate_manifest(root: Path) -> ChecksumManifest:
    """Generate checksum manifest for critical files.

    Args:
        root: Project root directory.

    Returns:
        ChecksumManifest with all file checksums.
    """
    manifest = ChecksumManifest(
        version="1.0",
        generated_at=datetime.now().isoformat(),
    )

    files = find_critical_files(root)

    for file_path, category in files:
        try:
            rel_path = str(file_path.relative_to(root))
            stat = file_path.stat()

            manifest.files[rel_path] = FileChecksum(
                path=rel_path,
                sha256=compute_sha256(file_path),
                category=category,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            )
        except Exception as e:
            logger.warning("Could not process %s: %s", file_path, e)

    return manifest


def load_manifest(manifest_path: Path) -> ChecksumManifest | None:
    """Load checksum manifest from file.

    Args:
        manifest_path: Path to manifest JSON file.

    Returns:
        ChecksumManifest or None if not found.
    """
    if not manifest_path.exists():
        return None

    try:
        with open(manifest_path) as f:
            data = json.load(f)
        return ChecksumManifest.from_dict(data)
    except Exception as e:
        logger.error("Failed to load manifest: %s", e)
        return None


def save_manifest(manifest: ChecksumManifest, manifest_path: Path) -> None:
    """Save checksum manifest to file.

    Args:
        manifest: Manifest to save.
        manifest_path: Output path.
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, "w") as f:
        json.dump(manifest.to_dict(), f, indent=2)


def _current_critical_files(root: Path) -> dict[str, tuple[Path, str]]:
    return {
        str(path.relative_to(root)): (path, category)
        for path, category in find_critical_files(root)
    }


def _verified_manifest_result(
    *,
    rel_path: str,
    file_path: Path,
    category: str,
    expected: FileChecksum,
) -> VerificationResult:
    actual_hash = compute_sha256(file_path)
    actual_size = file_path.stat().st_size
    status = "ok" if actual_hash == expected.sha256 else "modified"
    return VerificationResult(
        path=rel_path,
        category=category,
        status=status,
        expected_hash=expected.sha256,
        actual_hash=actual_hash,
        size_change=actual_size - expected.size if status == "modified" else None,
    )


def _verify_manifest_entry(
    *,
    rel_path: str,
    current_file: tuple[Path, str] | None,
    expected: FileChecksum,
) -> VerificationResult:
    if current_file is None:
        return VerificationResult(
            path=rel_path,
            category=expected.category,
            status="missing",
            expected_hash=expected.sha256,
        )

    file_path, category = current_file
    try:
        return _verified_manifest_result(
            rel_path=rel_path,
            file_path=file_path,
            category=category,
            expected=expected,
        )
    except Exception as e:
        logger.warning("Could not verify %s: %s", rel_path, e)
        return VerificationResult(
            path=rel_path,
            category=expected.category,
            status="error",
        )


def _new_file_result(
    rel_path: str,
    file_path: Path,
    category: str,
) -> VerificationResult | None:
    try:
        return VerificationResult(
            path=rel_path,
            category=category,
            status="new",
            actual_hash=compute_sha256(file_path),
        )
    except Exception:
        return None


def verify_checksums(
    root: Path,
    manifest: ChecksumManifest,
) -> VerificationReport:
    """Verify current files against manifest.

    Args:
        root: Project root directory.
        manifest: Reference manifest.

    Returns:
        VerificationReport with all results.
    """
    report = VerificationReport(
        manifest_version=manifest.version,
        manifest_date=manifest.generated_at,
    )

    current_files = _current_critical_files(root)

    for rel_path, expected in manifest.files.items():
        current_file = current_files.pop(rel_path, None)
        report.results.append(
            _verify_manifest_entry(
                rel_path=rel_path,
                current_file=current_file,
                expected=expected,
            )
        )

    for rel_path, (file_path, category) in current_files.items():
        if result := _new_file_result(rel_path, file_path, category):
            report.results.append(result)

    return report


# =============================================================================
# CLI Interface
# =============================================================================


def _results_by_status(report: VerificationReport) -> dict[str, list[VerificationResult]]:
    by_status: dict[str, list[VerificationResult]] = {}
    for result in report.results:
        by_status.setdefault(result.status, []).append(result)
    return by_status


def _log_missing_files(results: list[VerificationResult]) -> None:
    logger.info("## MISSING FILES (%d)", len(results))
    for result in results:
        logger.info("  [!] %s", result.path)
    logger.info("")


def _log_modified_files(results: list[VerificationResult]) -> None:
    logger.info("## MODIFIED FILES (%d)", len(results))
    for result in results:
        size_info = ""
        if result.size_change:
            size_info = f" ({result.size_change:+d} bytes)"
        logger.info("  [M] %s%s", result.path, size_info)
        logger.info(
            "      Expected: %s...",
            result.expected_hash[:16] if result.expected_hash else "N/A",
        )
        logger.info(
            "      Actual:   %s...",
            result.actual_hash[:16] if result.actual_hash else "N/A",
        )
    logger.info("")


def _log_new_files(results: list[VerificationResult]) -> None:
    logger.info("## NEW FILES (%d) - not in manifest", len(results))
    for result in results:
        logger.info("  [+] %s", result.path)
    logger.info("")


def log_report_text(report: VerificationReport) -> None:
    """Log text verification report."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Checksum Verification Report")
    logger.info("=" * 70)
    logger.info("")

    if report.manifest_date:
        logger.info("Manifest version: %s", report.manifest_version)
        logger.info("Manifest date:    %s", report.manifest_date)
        logger.info("")

    by_status = _results_by_status(report)

    if "missing" in by_status:
        _log_missing_files(by_status["missing"])

    if "modified" in by_status:
        _log_modified_files(by_status["modified"])

    if "new" in by_status:
        _log_new_files(by_status["new"])

    # Summary
    logger.info("=" * 70)
    logger.info("Summary:")
    logger.info("  OK:       %d", report.ok_count)
    logger.info("  Modified: %d", report.modified_count)
    logger.info("  Missing:  %d", report.missing_count)
    logger.info("  New:      %d", report.new_count)
    logger.info("")

    if report.passed:
        logger.info("Result: PASSED - All critical files verified")
    else:
        logger.info("Result: FAILED - Critical files have been modified or are missing")

    logger.info("=" * 70)


def log_report_json(report: VerificationReport) -> None:
    """Log JSON verification report."""
    output = {
        "manifest_version": report.manifest_version,
        "manifest_date": report.manifest_date,
        "passed": report.passed,
        "summary": {
            "ok": report.ok_count,
            "modified": report.modified_count,
            "missing": report.missing_count,
            "new": report.new_count,
        },
        "results": [
            {
                "path": r.path,
                "category": r.category,
                "status": r.status,
                "expected_hash": r.expected_hash,
                "actual_hash": r.actual_hash,
                "size_change": r.size_change,
            }
            for r in report.results
        ],
    }
    logger.info(json.dumps(output, indent=2))


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BioETL Checksum Verification Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate new checksum manifest",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Manifest file path (default: {DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root path",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    return parser.parse_args()


def _category_counts(manifest: ChecksumManifest) -> dict[str, int]:
    counts: dict[str, int] = {}
    for file_checksum in manifest.files.values():
        counts[file_checksum.category] = counts.get(file_checksum.category, 0) + 1
    return counts


def _log_generated_manifest(manifest: ChecksumManifest, manifest_path: Path) -> None:
    logger.info("")
    logger.info("Manifest generated: %s", manifest_path)
    logger.info("Files included: %d", len(manifest.files))
    logger.info("")
    logger.info("By category:")
    for category, count in sorted(_category_counts(manifest).items()):
        logger.info("  %s: %d", category, count)


def _generate_manifest_flow(root: Path, manifest_path: Path) -> int:
    logger.info("Generating checksum manifest...")
    manifest = generate_manifest(root)
    save_manifest(manifest, manifest_path)
    _log_generated_manifest(manifest, manifest_path)
    return 0


def _load_manifest_or_error(manifest_path: Path) -> ChecksumManifest | None:
    loaded_manifest = load_manifest(manifest_path)
    if loaded_manifest is not None:
        return loaded_manifest
    logger.error("Manifest not found: %s", manifest_path)
    logger.info("Run with --generate to create a new manifest.")
    return None


def _emit_verification_report(report: VerificationReport, *, as_json: bool) -> None:
    if as_json:
        log_report_json(report)
        return
    log_report_text(report)


def main() -> int:
    """Entry point."""
    args = parse_args()

    root = args.path.resolve()
    if not root.exists():
        logger.error("Path does not exist: %s", root)
        return 2

    if args.generate:
        return _generate_manifest_flow(root, args.manifest)

    loaded_manifest = _load_manifest_or_error(args.manifest)
    if loaded_manifest is None:
        return 2

    report = verify_checksums(root, loaded_manifest)
    _emit_verification_report(report, as_json=args.json)

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
