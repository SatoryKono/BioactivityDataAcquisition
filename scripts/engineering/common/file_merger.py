#!/usr/bin/env python3
"""File merger script for combining multiple files into a single output file.

This script recursively traverses a directory, filters files by extensions,
and combines their contents into a single output file with metadata headers.
"""

import argparse
import sys
from pathlib import Path

DEFAULT_EXCLUDE_DIRS = (
    "__pycache__,.git,.venv,node_modules,.ai,data,.worktrees,"
    ".cache,.pytest_cache,reports,logs,output"
)


def get_project_root() -> Path:
    """Get the project root directory.

    Returns the project root directory by going up from the script location.
    Script is located in scripts/engineering/common/, so project root is three
    directory levels above its containing directory.

    Returns:
        Path to project root directory.
    """
    # Get the directory where this script is located
    script_dir = Path(__file__).resolve().parent
    # common/ -> engineering/ -> scripts/ -> project root
    project_root = script_dir.parents[2]
    return project_root


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
  # Standard mode
  python -m scripts.engineering.common.file_merger -i ./src -o combined.txt
  python -m scripts.engineering.common.file_merger -i ./docs -e md -o docs_combined.md --sort by_extension

  # Project code merge mode (creates 5 files by architectural layers)
  python -m scripts.engineering.common.file_merger --merge_project_code

  # Documentation merge mode (merges all docs/*.md into one file)
  python -m scripts.engineering.common.file_merger --merge_documentation
  python -m scripts.engineering.common.file_merger --merge_documentation -o my_docs.md

  # Configs merge mode (merges all configs/*.yaml into one file)
  python -m scripts.engineering.common.file_merger --merge_configs
  python -m scripts.engineering.common.file_merger --merge_configs -o my_configs.md

  # Project structure mode (creates tree structure of all project files)
  python -m scripts.engineering.common.file_merger --project_structure
  python -m scripts.engineering.common.file_merger --project_structure -o structure.md

  # All merge modes at once (creates all output files in reports/)
  python -m scripts.engineering.common.file_merger --merge_all
        """,
    )

    parser.add_argument(
        "-i",
        "--input-dir",
        required=False,
        type=Path,
        help="Input directory to scan (required unless special mode is used)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("reports/merged_output.txt"),
        help="Output file path (default: reports/merged_output.txt)",
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
        default=DEFAULT_EXCLUDE_DIRS,
        help=(
            f"Comma-separated directories to exclude (default: {DEFAULT_EXCLUDE_DIRS})"
        ),
    )

    parser.add_argument(
        "--sort",
        choices=["alphabetical", "by_extension", "none"],
        default="alphabetical",
        help="File sorting method (default: alphabetical)",
    )

    parser.add_argument(
        "--merge_project_code",
        action="store_true",
        help="Special mode: merge code from src/bioetl/ layers into 5 separate files (one per layer)",
    )

    parser.add_argument(
        "--merge_documentation",
        action="store_true",
        help="Special mode: merge all markdown files from docs/ into one file (default: documentation_merged.md)",
    )

    parser.add_argument(
        "--merge_configs",
        action="store_true",
        help="Special mode: merge all YAML files from configs/ into one file (default: configs_merged.md)",
    )

    parser.add_argument(
        "--project_structure",
        action="store_true",
        help="Special mode: create tree structure of all project files (default: project_structure.md)",
    )

    parser.add_argument(
        "--merge_all",
        action="store_true",
        help="Execute all merge modes: --merge_project_code --merge_documentation --merge_configs --project_structure",
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
) -> list[Path]:
    """Recursively collect files matching specified extensions.

    Args:
        input_dir: Root directory to scan.
        extensions: Set of file extensions to include (without dots).
        exclude_dirs: Set of directory names to exclude.

    Returns:
        List of Path objects for matching files.
    """
    files: list[Path] = []

    for item in input_dir.rglob("*"):
        # Skip excluded directories
        if any(should_exclude_dir(parent, exclude_dirs) for parent in item.parents):
            continue

        # Check if file matches extensions
        if item.is_file() and item.suffix.lstrip(".") in extensions:
            files.append(item)

    return files


def sort_files(files: list[Path], sort_method: str) -> list[Path]:
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


def _tree_child_prefix(prefix: str, is_last: bool) -> str:
    return prefix + ("    " if is_last else "│   ")


def _format_tree_node(
    prefix: str, name: str, *, is_dir: bool = False, is_last: bool = True
) -> str:
    suffix = "/" if is_dir else ""
    if prefix == "":
        return f"{name}{suffix}"
    connector = "└── " if is_last else "├── "
    return f"{prefix}{connector}{name}{suffix}"


def _iter_tree_items(directory: Path, exclude_dirs: set[str]) -> list[Path] | None:
    try:
        items = sorted(
            directory.iterdir(), key=lambda path: (not path.is_dir(), path.name)
        )
    except (PermissionError, OSError):
        return None
    return [item for item in items if not (item.is_dir() and item.name in exclude_dirs)]


def merge_files(
    files: list[Path], output_file: Path, input_dir: Path, encoding: str
) -> tuple[int, int, dict[str, int]]:
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
    extension_counts: dict[str, int] = {}

    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    output_file = resolve_output_path(output_file, root=REPO_ROOT)
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
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def print_statistics(
    files_processed: int, total_bytes: int, extension_counts: dict[str, int]
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


def merge_project_code_layers(
    encoding: str, exclude_dirs: set[str], sort_method: str
) -> int:
    """Merge project code by architectural layers.

    Creates 5 output files, one for each layer:
    - interfaces_merged.md
    - infrastructure_merged.md
    - domain_merged.md
    - composition_merged.md
    - application_merged.md

    Args:
        encoding: File encoding.
        exclude_dirs: Set of directory names to exclude.
        sort_method: File sorting method.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    # Define project layers
    layers = ["interfaces", "infrastructure", "domain", "composition", "application"]

    # Base directory for project code
    project_root = get_project_root()
    base_dir = project_root / "src" / "bioetl"

    # Reports output directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    if not base_dir.exists():
        print(
            f"Error: Project directory does not exist: {base_dir}",
            file=sys.stderr,
        )
        return 1

    print("=" * 80)
    print("PROJECT CODE MERGE MODE")
    print("=" * 80)
    print(f"Base directory: {base_dir}")
    print(f"Layers: {', '.join(layers)}")
    print("Output files: {layer}_merged.md")
    print("=" * 80)

    # Extensions for Python code
    extensions = {"py"}

    # Process each layer
    total_files = 0
    total_size = 0

    for layer in layers:
        layer_dir = base_dir / layer

        if not layer_dir.exists():
            print(f"\nWarning: Layer directory not found: {layer_dir}", file=sys.stderr)
            continue

        print(f"\nProcessing layer: {layer}")

        # Collect files for this layer
        files = collect_files(layer_dir, extensions, exclude_dirs)

        if not files:
            print(f"  No Python files found in {layer_dir}")
            continue

        print(f"  Found {len(files)} file(s)")

        # Sort files
        files = sort_files(files, sort_method)

        # Create output file for this layer
        output_file = reports_dir / f"{layer}_merged.md"

        # Merge files
        files_processed, layer_size, _extension_counts = merge_files(
            files, output_file, layer_dir, encoding
        )

        total_files += files_processed
        total_size += layer_size

        print(f"  Wrote {files_processed} file(s) to {output_file}")
        print(f"  Size: {format_bytes(layer_size)}")

    # Print overall statistics
    print("\n" + "=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    print(f"Total files processed: {total_files}")
    print(f"Total size: {format_bytes(total_size)}")
    print(f"Output files created: {len(layers)}")
    print("=" * 80)

    return 0


def merge_documentation(
    output_file: Path, encoding: str, exclude_dirs: set[str], sort_method: str
) -> int:
    """Merge all documentation markdown files into a single output file.

    Merges all .md files from docs/ directory into one file.
    Default output: documentation_merged.md

    Args:
        output_file: Output file path.
        encoding: File encoding.
        exclude_dirs: Set of directory names to exclude.
        sort_method: File sorting method.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    # Documentation directory
    project_root = get_project_root()
    docs_dir = project_root / "docs"

    if not docs_dir.exists():
        print(
            f"Error: Documentation directory does not exist: {docs_dir}",
            file=sys.stderr,
        )
        return 1

    if not docs_dir.is_dir():
        print(
            f"Error: Documentation path is not a directory: {docs_dir}",
            file=sys.stderr,
        )
        return 1

    print("=" * 80)
    print("DOCUMENTATION MERGE MODE")
    print("=" * 80)
    print(f"Source directory: {docs_dir}")
    print(f"Output file: {output_file}")
    print("=" * 80)

    # Extensions for documentation
    extensions = {"md"}

    # Collect files
    print(f"\nScanning {docs_dir} for markdown files...")
    files = collect_files(docs_dir, extensions, exclude_dirs)

    if not files:
        print("Warning: No markdown files found in docs/", file=sys.stderr)
        return 0

    print(f"Found {len(files)} markdown file(s)")

    # Sort files
    files = sort_files(files, sort_method)

    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Merge files
    print(f"Merging files into: {output_file}")
    files_processed, total_bytes, extension_counts = merge_files(
        files, output_file, docs_dir, encoding
    )

    # Print statistics
    print_statistics(files_processed, total_bytes, extension_counts)

    print(f"\nSuccessfully wrote to: {output_file}")
    return 0


def generate_tree_structure(
    directory: Path,
    exclude_dirs: set[str],
    prefix: str = "",
    is_last: bool = True,
) -> list[str]:
    """Generate tree structure lines for a directory.

    Args:
        directory: Directory to generate tree for.
        exclude_dirs: Set of directory names to exclude.
        prefix: Current line prefix for indentation.
        is_last: Whether this is the last item in parent directory.

    Returns:
        List of formatted tree lines.
    """
    lines: list[str] = []

    dir_name = directory.name if directory.name else str(directory)
    lines.append(_format_tree_node(prefix, dir_name, is_dir=True, is_last=is_last))

    items = _iter_tree_items(directory, exclude_dirs)
    if items is None:
        return lines

    # Process items
    for idx, item in enumerate(items):
        is_last_item = idx == len(items) - 1
        child_prefix = _tree_child_prefix(prefix, is_last)

        if item.is_symlink():
            lines.append(
                _format_tree_node(child_prefix, f"{item.name}@", is_last=is_last_item)
            )
            continue
        if item.is_dir():
            lines.extend(
                generate_tree_structure(item, exclude_dirs, child_prefix, is_last_item)
            )
            continue
        lines.append(_format_tree_node(child_prefix, item.name, is_last=is_last_item))

    return lines


def create_project_structure(
    output_file: Path, encoding: str, exclude_dirs: set[str]
) -> int:
    """Create a tree structure of all project files.

    Creates a markdown file with ASCII tree representation of project structure.
    Default output: project_structure.md

    Args:
        output_file: Output file path.
        encoding: File encoding.
        exclude_dirs: Set of directory names to exclude.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    # Project root directory
    root_dir = get_project_root()

    print("=" * 80)
    print("PROJECT STRUCTURE MODE")
    print("=" * 80)
    print(f"Root directory: {root_dir.resolve()}")
    print(f"Output file: {output_file}")
    print(f"Excluding directories: {', '.join(sorted(exclude_dirs))}")
    print("=" * 80)

    print("\nGenerating project structure tree...")

    # Generate tree structure
    tree_lines = generate_tree_structure(root_dir, exclude_dirs)

    # Count files and directories
    total_lines = len(tree_lines)
    file_count = sum(1 for line in tree_lines if not line.rstrip().endswith("/"))
    dir_count = total_lines - file_count

    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write to output file
    try:
        with output_file.open("w", encoding=encoding) as f:
            f.write("# Project Structure\n\n")
            f.write(f"Generated: {root_dir.resolve()}\n\n")
            f.write("```\n")
            for line in tree_lines:
                f.write(line + "\n")
            f.write("```\n\n")
            f.write("**Statistics:**\n")
            f.write(f"- Directories: {dir_count}\n")
            f.write(f"- Files: {file_count}\n")
            f.write(f"- Total items: {total_lines}\n")

        print("\nTree structure generated successfully!")
        print(f"Directories: {dir_count}")
        print(f"Files: {file_count}")
        print(f"Total items: {total_lines}")
        print(f"\nSuccessfully wrote to: {output_file}")

        return 0

    except Exception as e:
        print(f"Error writing to file: {e}", file=sys.stderr)
        return 1


def merge_configs(
    output_file: Path, encoding: str, exclude_dirs: set[str], sort_method: str
) -> int:
    """Merge all configuration YAML files into a single output file.

    Merges all .yaml and .yml files from configs/ directory into one file.
    Default output: configs_merged.md

    Args:
        output_file: Output file path.
        encoding: File encoding.
        exclude_dirs: Set of directory names to exclude.
        sort_method: File sorting method.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    # Configuration directory
    project_root = get_project_root()
    configs_dir = project_root / "configs"

    if not configs_dir.exists():
        print(
            f"Error: Configuration directory does not exist: {configs_dir}",
            file=sys.stderr,
        )
        return 1

    if not configs_dir.is_dir():
        print(
            f"Error: Configuration path is not a directory: {configs_dir}",
            file=sys.stderr,
        )
        return 1

    print("=" * 80)
    print("CONFIGS MERGE MODE")
    print("=" * 80)
    print(f"Source directory: {configs_dir}")
    print(f"Output file: {output_file}")
    print("=" * 80)

    # Extensions for YAML configuration files
    extensions = {"yaml", "yml"}

    # Collect files
    print(f"\nScanning {configs_dir} for YAML files...")
    files = collect_files(configs_dir, extensions, exclude_dirs)

    if not files:
        print("Warning: No YAML files found in configs/", file=sys.stderr)
        return 0

    print(f"Found {len(files)} YAML file(s)")

    # Sort files
    files = sort_files(files, sort_method)

    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Merge files
    print(f"Merging files into: {output_file}")
    files_processed, total_bytes, extension_counts = merge_files(
        files, output_file, configs_dir, encoding
    )

    # Print statistics
    print_statistics(files_processed, total_bytes, extension_counts)

    print(f"\nSuccessfully wrote to: {output_file}")
    return 0


def _resolve_mode_output(
    current_output: Path,
    default_output: Path,
    fallback_output: str,
) -> Path:
    """Use a mode-specific output path when the CLI kept the generic default."""
    if current_output == default_output:
        return Path(fallback_output)
    return current_output


def _run_special_modes(
    args: argparse.Namespace, exclude_dirs: set[str]
) -> tuple[bool, int]:
    """Execute selected special modes and return (executed_any, exit_code)."""
    default_output = Path("reports/merged_output.txt")
    exit_code = 0
    executed_any = False

    if args.merge_project_code:
        executed_any = True
        result = merge_project_code_layers(args.encoding, exclude_dirs, args.sort)
        if result != 0:
            exit_code = result

    mode_specs = (
        (
            args.merge_documentation,
            "reports/documentation_merged.md",
            lambda output: merge_documentation(
                output, args.encoding, exclude_dirs, args.sort
            ),
        ),
        (
            args.merge_configs,
            "reports/configs_merged.md",
            lambda output: merge_configs(
                output, args.encoding, exclude_dirs, args.sort
            ),
        ),
        (
            args.project_structure,
            "reports/project_structure.md",
            lambda output: create_project_structure(
                output, args.encoding, exclude_dirs
            ),
        ),
    )

    for enabled, fallback_output, runner in mode_specs:
        if not enabled:
            continue
        executed_any = True
        output_file = _resolve_mode_output(args.output, default_output, fallback_output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        result = runner(output_file)
        if result != 0:
            exit_code = result

    return executed_any, exit_code


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    args = parse_arguments()

    # Parse exclude dirs (used in all modes)
    exclude_dirs = {d.strip() for d in args.exclude_dirs.split(",")}

    # Expand --merge_all into individual flags
    if args.merge_all:
        args.merge_project_code = True
        args.merge_documentation = True
        args.merge_configs = True
        args.project_structure = True

    executed_any, exit_code = _run_special_modes(args, exclude_dirs)

    if executed_any:
        return exit_code

    # Standard mode - validate input directory is required
    if not args.input_dir:
        print(
            "Error: --input-dir is required when not using special mode",
            file=sys.stderr,
        )
        return 1

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

    # Parse extensions
    extensions = {ext.strip().lstrip(".") for ext in args.extensions.split(",")}

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

    # Create output directory if needed
    args.output.parent.mkdir(parents=True, exist_ok=True)

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
