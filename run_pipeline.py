#!/usr/bin/env python
"""Unified wrapper script to run pipelines.

Usage:
    python run_pipeline.py activity       # Run chembl.activity pipeline
    python run_pipeline.py chembl.assay   # Run chembl.assay pipeline
    python run_pipeline.py --list         # List available pipelines

This script dynamically discovers pipeline configurations from the
configs/pipelines directory and supports running any configured pipeline.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# Root directory for this project
REPO_ROOT = Path(__file__).resolve().parent
PIPELINES_ROOT = REPO_ROOT / "configs" / "pipelines"


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file without importing heavy dependencies."""
    import yaml  # Lazy import

    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def discover_pipelines() -> dict[str, dict[str, str]]:
    """Discover available pipelines from config files.

    Returns:
        Dictionary mapping shorthand names to pipeline info:
        - 'config': path to config file
        - 'name': pipeline name from config
        - 'output': output path from config
    """
    pipelines: dict[str, dict[str, str]] = {}

    if not PIPELINES_ROOT.exists():
        return pipelines

    for config_path in sorted(PIPELINES_ROOT.rglob("*.yaml")):
        try:
            config = _load_yaml(config_path)
        except Exception as e:
            # Log error but continue processing other files
            print(f"Warning: Failed to load {config_path.relative_to(REPO_ROOT)}: {e}", file=sys.stderr)
            continue

        # Extract pipeline info from config
        pipeline_id = config.get("id", "")
        entity = config.get("entity", config_path.stem)
        pipeline_name = config.get("pipeline", {}).get("name", f"{entity}_chembl")
        output_path = config.get("output_path", f"data/output/{entity}")

        # Use relative config path
        rel_config = config_path.relative_to(REPO_ROOT)

        pipeline_info = {
            "config": str(rel_config),
            "name": pipeline_name,
            "output": output_path,
        }

        # Register by full pipeline_id (e.g., "chembl.activity")
        if pipeline_id:
            pipelines[pipeline_id] = pipeline_info

        # Also register by entity shorthand (e.g., "activity")
        if entity and entity not in pipelines:
            pipelines[entity] = pipeline_info

    return pipelines


def list_pipelines() -> None:
    """Print list of available pipelines."""
    pipelines = discover_pipelines()

    if not pipelines:
        print("No pipelines found in configs/pipelines/")
        return

    print("Available pipelines:")
    print()

    # Group by provider
    seen_configs: set[str] = set()
    for key in sorted(pipelines.keys()):
        info = pipelines[key]
        config = info["config"]
        if config in seen_configs:
            continue
        seen_configs.add(config)

        print(f"  {key:20} -> {config}")
    print()
    print("Usage: python run_pipeline.py <pipeline> [--limit N] [--dry-run]")


def main() -> None:
    """Configure path, set arguments, and run the CLI app."""
    # Handle --list flag
    if len(sys.argv) >= 2 and sys.argv[1] in ("--list", "-l"):
        list_pipelines()
        return

    # Discover available pipelines
    pipelines = discover_pipelines()

    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(f"Usage: {sys.argv[0]} <pipeline> [options]")
        print(f"       {sys.argv[0]} --list")
        print()
        print("Available pipelines:")
        for key in sorted(set(p["config"] for p in pipelines.values())):
            # Find entity name for this config
            entity = next(
                k for k, v in pipelines.items() if v["config"] == key and "." not in k
            )
            print(f"  {entity}")
        sys.exit(0 if "--help" in sys.argv or "-h" in sys.argv else 1)

    pipeline_key = sys.argv[1]
    if pipeline_key not in pipelines:
        print(f"Error: Unknown pipeline '{pipeline_key}'")
        print("Use --list to see available pipelines")
        sys.exit(1)

    pipeline = pipelines[pipeline_key]

    # Configure path
    src_dir = REPO_ROOT / "src"
    src_str = str(src_dir)
    if src_str in sys.path:
        sys.path.remove(src_str)
    sys.path.insert(0, src_str)

    from bioetl.interfaces.cli.app import app

    # Set CLI arguments
    # Pass through additional CLI arguments (e.g., --limit, --dry-run)
    base_args = [
        "bioetl",
        "run",
        pipeline["name"],
        "--config",
        pipeline["config"],
        "--output",
        pipeline["output"],
    ]
    # Append any additional arguments passed to this script
    sys.argv = base_args + sys.argv[2:]
    app()


if __name__ == "__main__":
    main()
