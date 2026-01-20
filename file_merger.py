#!/usr/bin/env python3
"""File merger script for combining multiple files into a single output file.

This script recursively traverses a directory, filters files by extensions,
and combines their contents into a single output file with metadata headers.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Recursively merge files from a directory into a single output file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python file_merger.py -i ./src -o combined.txt
  python file_merger.py -i ./docs -e md -o docs_combined.md --sort by_extension
        """,
    )

    parser.add_argument(
        "-i",
        "--input-dir",
        required=True,
        type=Path,
        help="Input directory to scan (required)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("merged_output.txt"),
        help="Output file path (default: merged_output.txt)",
    )

    parser.add_argument(
        "-e",
        "--extensions",
        type=str,
        default="md,py",
        help="Comma-separated file extensions to include (default: md,py)",
    )

    parser.add_argument(
        "--encoding",
        type=str,
        default="utf-8",
        help="File encoding (default: utf-8)",
    )

    parser.add_argument(
        "--exclude-dirs",
        type=str,
        default="__pycache__,.git,.venv,node_modules",
        help="Comma-separated directories to exclude (default: __pycache__,.git,.venv,node_modules)",
    )

    parser.add_argument(
        "--sort",
        choices=["alphabetical", "by_extension", "none"],
        default="alphabetical",
        help="File sorting method (default: alphabetical)",
    )

    return parser.parse_args()


def should_exclude_dir(dir_path: Path, exclude_dirs: set[str]) -> bool:
    """Check if directory should be excluded from traversal.

    Args:
        dir_path: Directory path to check.
        exclude_dirs: Set of directory names to exclude.

    Returns:
        True if directory should be excluded, False otherwise.
    """
    return dir_path.name in exclude_dirs


def collect_files(
    input_dir: Path, extensions: set[str], exclude_dirs: set[str]
) -> List[Path]:
    """Recursively collect files matching specified extensions.

    Args:
        input_dir: Root directory to scan.
        extensions: Set of file extensions to include (without dots).
        exclude_dirs: Set of directory names to exclude.

    Returns:
        List of Path objects for matching files.
    """
    files: List[Path] = []

    for item in input_dir.rglob("*"):
        # Skip excluded directories
        if any(should_exclude_dir(parent, exclude_dirs) for parent in item.parents):
            continue

        # Check if file matches extensions
        if item.is_file() and item.suffix.lstrip(".") in extensions:
            files.append(item)

    return files


def sort_files(files: List[Path], sort_method: str) -> List[Path]:
    """Sort files according to specified method.

    Args:
        files: List of file paths.
        sort_method: Sorting method - 'alphabetical', 'by_extension', or 'none'.

    Returns:
        Sorted list of file paths.
    """
    if sort_method == "alphabetical":
        return sorted(files, key=lambda p: str(p))
    elif sort_method == "by_extension":
        return sorted(files, key=lambda p: (p.suffix, str(p)))
    else:  # none
        return files


def merge_files(
    files: List[Path], output_file: Path, input_dir: Path, encoding: str
) -> Tuple[int, int, Dict[str, int]]:
    """Merge files into a single output file.

    Args:
        files: List of file paths to merge.
        output_file: Output file path.
        input_dir: Input directory (for relative path calculation).
        encoding: File encoding.

    Returns:
        Tuple of (files_processed, total_bytes, extension_counts).
    """
    files_processed = 0
    total_bytes = 0
    extension_counts: Dict[str, int] = {}

    with output_file.open("w", encoding=encoding) as outf:
        for file_path in files:
            try:
                # Calculate relative paths
                rel_path = file_path.relative_to(input_dir)

                # Read file content
                content = file_path.read_text(encoding=encoding)
                file_size = len(content.encode(encoding))

                # Write header and content
                separator = "=" * 80
                outf.write(f"{separator}\n")
                outf.write(f"File: {file_path.name}\n")
                outf.write(f"Path: {rel_path}\n")
                outf.write(f"{separator}\n")
                outf.write(content)
                if not content.endswith("\n"):
                    outf.write("\n")
                outf.write("\n")

                # Update statistics
                files_processed += 1
                total_bytes += file_size
                ext = file_path.suffix.lstrip(".")
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

            except UnicodeDecodeError as e:
                print(
                    f"Warning: Skipping {file_path} due to encoding error: {e}",
                    file=sys.stderr,
                )
            except Exception as e:
                print(
                    f"Warning: Skipping {file_path} due to error: {e}",
                    file=sys.stderr,
                )

    return files_processed, total_bytes, extension_counts


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string.

    Args:
        num_bytes: Number of bytes.

    Returns:
        Formatted string (e.g., '1.5 KB', '2.3 MB').
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def print_statistics(
    files_processed: int, total_bytes: int, extension_counts: Dict[str, int]
) -> None:
    """Print processing statistics.

    Args:
        files_processed: Number of files processed.
        total_bytes: Total size in bytes.
        extension_counts: Dictionary mapping extensions to file counts.
    """
    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)
    print(f"Files processed: {files_processed}")
    print(f"Total size: {format_bytes(total_bytes)}")
    print("\nBreakdown by extension:")
    for ext, count in sorted(extension_counts.items()):
        print(f"  .{ext}: {count} file(s)")
    print("=" * 80)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    args = parse_arguments()

    # Validate input directory
    if not args.input_dir.exists():
        print(
            f"Error: Input directory does not exist: {args.input_dir}",
            file=sys.stderr,
        )
        return 1

    if not args.input_dir.is_dir():
        print(
            f"Error: Input path is not a directory: {args.input_dir}",
            file=sys.stderr,
        )
        return 1

    # Parse extensions and exclude dirs
    extensions = {ext.strip().lstrip(".") for ext in args.extensions.split(",")}
    exclude_dirs = {d.strip() for d in args.exclude_dirs.split(",")}

    # Collect files
    print(f"Scanning directory: {args.input_dir}")
    print(f"Extensions: {', '.join(sorted(extensions))}")
    print(f"Excluding directories: {', '.join(sorted(exclude_dirs))}")

    files = collect_files(args.input_dir, extensions, exclude_dirs)

    if not files:
        print("Warning: No files found matching criteria.", file=sys.stderr)
        return 0

    print(f"Found {len(files)} file(s)")

    # Sort files
    files = sort_files(files, args.sort)

    # Merge files
    print(f"Merging files into: {args.output}")
    files_processed, total_bytes, extension_counts = merge_files(
        files, args.output, args.input_dir, args.encoding
    )

    # Print statistics
    print_statistics(files_processed, total_bytes, extension_counts)

    print(f"\nSuccessfully wrote to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
