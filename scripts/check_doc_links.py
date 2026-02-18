#!/usr/bin/env python3
"""check_doc_links.py - Validate documentation links and spec file existence.

Checks:
  1. Markdown relative links in docs/ resolve to existing files
  2. Pipeline specs referenced in docs/04-reference/pipelines/README.md exist
  3. Config files referenced in pipeline YAML configs exist

Usage:
    python scripts/check_doc_links.py          # Full check
    python scripts/check_doc_links.py --specs   # Only spec file check
    python scripts/check_doc_links.py --links   # Only broken link check

Exit code: 0 = clean, 1 = violations found

References:
    - docs/04-reference/pipelines/README.md (canonical pipeline index)
    - ADR-027, ADR-028 (config structure)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
PIPELINES_DIR = DOCS_DIR / "04-reference" / "pipelines"

# Directories to skip
SKIP_DIRS = frozenset(
    {
        ".venv",
        "venv",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "build",
        "dist",
        "99-archive",
    }
)

# Regex to match markdown relative links: [text](path) — excludes http(s)
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((?!https?://|mailto:)([^)#]+)")


def _should_skip(path: Path) -> bool:
    """Return True if path should be excluded from scanning."""
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False


def check_broken_links(root: Path) -> list[tuple[Path, int, str, str]]:
    """Find broken relative markdown links in .md files under root.

    Returns list of (file, line_no, link_text, target_path).
    """
    broken: list[tuple[Path, int, str, str]] = []

    for md_file in sorted(root.rglob("*.md")):
        if _should_skip(md_file):
            continue

        try:
            lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for line_no, line in enumerate(lines, start=1):
            for match in MD_LINK_RE.finditer(line):
                link_text = match.group(1)
                raw_target = match.group(2).strip()

                # Skip *Spec pending* style entries
                if raw_target.startswith("*") or raw_target.startswith("{"):
                    continue

                # Resolve relative to the file's directory
                resolved = (md_file.parent / raw_target).resolve()

                if not resolved.exists():
                    broken.append((md_file, line_no, link_text, raw_target))

    return broken


def check_spec_files() -> list[tuple[str, str]]:
    """Verify that spec files referenced in pipeline README exist.

    Returns list of (pipeline_id, expected_path) for missing specs.
    """
    readme = PIPELINES_DIR / "README.md"
    if not readme.exists():
        return [("README.md", str(readme))]

    missing: list[tuple[str, str]] = []
    text = readme.read_text(encoding="utf-8", errors="replace")

    # Match [Spec](path) links
    for match in MD_LINK_RE.finditer(text):
        link_text = match.group(1)
        raw_target = match.group(2).strip()

        if "spec" not in link_text.lower() and "Spec" not in link_text:
            continue

        resolved = (PIPELINES_DIR / raw_target).resolve()
        if not resolved.exists():
            missing.append((link_text, raw_target))

    return missing


def check_config_existence() -> list[tuple[str, str]]:
    """Verify that configs referenced by convention exist.

    For each pipeline config in configs/pipelines/{provider}/{entity}.yaml,
    checks that the corresponding DQ and filter config files exist.
    """
    configs_dir = PROJECT_ROOT / "configs"
    pipelines_dir = configs_dir / "pipelines"
    missing: list[tuple[str, str]] = []

    if not pipelines_dir.exists():
        return missing

    for yaml_file in sorted(pipelines_dir.rglob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue

        # Skip composite configs
        if "composite" in yaml_file.parts:
            continue

        provider = yaml_file.parent.name
        entity = yaml_file.stem

        # Check DQ config
        dq_config = configs_dir / "quality" / "entities" / provider / f"{entity}.yaml"
        if not dq_config.exists():
            missing.append(
                (f"{provider}/{entity}", f"configs/quality/entities/{provider}/{entity}.yaml")
            )

        # Check filter config
        filter_config = configs_dir / "filters" / "entities" / provider / f"{entity}.yaml"
        if not filter_config.exists():
            missing.append(
                (f"{provider}/{entity}", f"configs/filters/entities/{provider}/{entity}.yaml")
            )

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Check documentation links and spec files")
    parser.add_argument("--links", action="store_true", help="Only check broken links")
    parser.add_argument("--specs", action="store_true", help="Only check spec files")
    parser.add_argument("--configs", action="store_true", help="Only check config existence")
    args = parser.parse_args()

    # Default: run all checks
    run_all = not (args.links or args.specs or args.configs)
    violations = 0

    if run_all or args.links:
        broken = check_broken_links(DOCS_DIR)
        if broken:
            print(f"\n{'='*60}")
            print(f"BROKEN LINKS ({len(broken)} found)")
            print(f"{'='*60}")
            for filepath, line_no, text, target in broken:
                rel = filepath.relative_to(PROJECT_ROOT)
                print(f"  {rel}:{line_no}: [{text}]({target})")
            violations += len(broken)
        else:
            print("Links: OK (no broken relative links found)")

    if run_all or args.specs:
        missing_specs = check_spec_files()
        if missing_specs:
            print(f"\n{'='*60}")
            print(f"MISSING SPEC FILES ({len(missing_specs)} found)")
            print(f"{'='*60}")
            for label, path in missing_specs:
                print(f"  {label} -> {path}")
            violations += len(missing_specs)
        else:
            print("Specs: OK (all referenced spec files exist)")

    if run_all or args.configs:
        missing_configs = check_config_existence()
        if missing_configs:
            print(f"\n{'='*60}")
            print(f"MISSING CONFIG FILES ({len(missing_configs)} found)")
            print(f"{'='*60}")
            for pipeline, path in missing_configs:
                print(f"  {pipeline} -> {path}")
            violations += len(missing_configs)
        else:
            print("Configs: OK (all convention-based config files exist)")

    if violations:
        print(f"\nTotal violations: {violations}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
