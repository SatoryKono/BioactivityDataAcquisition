#!/usr/bin/env python3
"""check_doc_links.py - Validate documentation links and spec file existence.

Checks:
  1. Markdown relative links in docs/ resolve to existing files
  2. Pipeline specs referenced in docs/04-reference/pipelines/README.md exist
  3. Config files referenced in pipeline YAML configs exist
  4. Legacy config/script tokens are absent in mkdocs nav docs

Usage:
    python scripts/check_doc_links.py          # Full check
    python scripts/check_doc_links.py --specs   # Only spec file check
    python scripts/check_doc_links.py --links   # Only broken link check
    python scripts/check_doc_links.py --legacy-paths   # Only legacy token check

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

import yaml

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
MD_PATH_RE = re.compile(r"[A-Za-z0-9_./-]+\.md")
LEGACY_DOC_TOKENS = (
    "configs/pipelines/",
    "configs/sources/",
    "scripts/validate-pipeline-configs.py",
)


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


def _load_nav_docs() -> list[Path]:
    """Load docs paths from mkdocs.yml navigation."""
    mkdocs_file = PROJECT_ROOT / "mkdocs.yml"
    if not mkdocs_file.exists():
        return []

    text = mkdocs_file.read_text(encoding="utf-8", errors="replace")
    nav_paths = sorted(set(MD_PATH_RE.findall(text)))
    return [DOCS_DIR / rel_path for rel_path in nav_paths]


def check_legacy_paths_in_nav_docs() -> list[tuple[Path, int, str]]:
    """Find legacy config/script tokens in active docs (mkdocs nav)."""
    violations: list[tuple[Path, int, str]] = []

    for md_file in _load_nav_docs():
        if not md_file.exists() or _should_skip(md_file):
            continue

        lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(lines, start=1):
            for token in LEGACY_DOC_TOKENS:
                if token in line:
                    violations.append((md_file, line_no, token))

    return violations


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
    """Verify that unified entity/provider configs are present and complete."""
    configs_dir = PROJECT_ROOT / "configs"
    entities_dir = configs_dir / "entities"
    providers_dir = configs_dir / "providers"
    missing: list[tuple[str, str]] = []

    if not entities_dir.exists():
        return missing

    for yaml_file in sorted(entities_dir.rglob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue

        provider = yaml_file.parent.name
        entity = yaml_file.stem

        payload = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}

        for section in ("pipeline", "schema", "quality", "filters", "contracts"):
            if section not in payload:
                missing.append(
                    (
                        f"{provider}/{entity}",
                        f"configs/entities/{provider}/{entity}.yaml::{section}",
                    )
                )

        provider_config = providers_dir / f"{provider}.yaml"
        if not provider_config.exists():
            missing.append(
                (
                    f"{provider}/{entity}",
                    f"configs/providers/{provider}.yaml",
                )
            )

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Check documentation links and spec files")
    parser.add_argument("--links", action="store_true", help="Only check broken links")
    parser.add_argument("--specs", action="store_true", help="Only check spec files")
    parser.add_argument("--configs", action="store_true", help="Only check config existence")
    parser.add_argument(
        "--legacy-paths",
        action="store_true",
        help="Only check legacy path tokens in mkdocs nav docs",
    )
    args = parser.parse_args()

    # Default: run all checks
    run_all = not (args.links or args.specs or args.configs or args.legacy_paths)
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

    if run_all or args.legacy_paths:
        legacy_hits = check_legacy_paths_in_nav_docs()
        if legacy_hits:
            print(f"\n{'='*60}")
            print(f"LEGACY PATH TOKENS ({len(legacy_hits)} found)")
            print(f"{'='*60}")
            for filepath, line_no, token in legacy_hits:
                rel = filepath.relative_to(PROJECT_ROOT)
                print(f"  {rel}:{line_no}: contains '{token}'")
            violations += len(legacy_hits)
        else:
            print("Legacy paths: OK (no legacy tokens in mkdocs nav docs)")

    if violations:
        print(f"\nTotal violations: {violations}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
