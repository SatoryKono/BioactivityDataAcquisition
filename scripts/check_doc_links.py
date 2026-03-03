#!/usr/bin/env python3
"""check_doc_links.py - Validate documentation links and spec file existence.

Checks:
  1. Markdown relative links in docs/ resolve to existing files
  2. Pipeline specs referenced in docs/04-reference/pipelines/README.md exist
  3. Config files referenced in pipeline YAML configs exist
  4. Gold contracts index matches exported JSON contracts
  5. ChEMBL provider overview matches provider docs inventory
  6. Doc drift guardrails are enforced in mkdocs nav docs:
     - canonical Delta token (`_delta_log`)
     - legacy config/script tokens
     - outdated `bioetl run <pipeline>` syntax
     - removed run flags (`--start-date`, `--end-date`, etc.)
     - legacy run flag (`--run_type`)
     - legacy system-field tokens (`-run-id`, `-ingestion-ts`, etc.)
     - legacy lineage log tokens (`lineage-log`, `sys.lineage-log`)
     - legacy docs path (`docs/pipelines/`)
     - invalid env var style (`BIOETL-...`)
     - invalid kebab-case Python snippets in fenced `python` blocks
     - path contracts for REQUIREMENTS and governance links

Usage:
    python scripts/check_doc_links.py          # Full check
    python scripts/check_doc_links.py --specs   # Only spec file check
    python scripts/check_doc_links.py --links   # Only broken link check
    python scripts/check_doc_links.py --contracts-index  # Gold contract index parity
    python scripts/check_doc_links.py --provider-overview  # Provider overview parity
    python scripts/check_doc_links.py --not-in-nav-growth   # Only not-in-nav growth guard
    python scripts/check_doc_links.py --legacy-paths   # Only doc drift guardrails
    python scripts/check_doc_links.py --legacy-paths-all   # Drift guardrails incl. internal nav docs

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
GOLD_SCHEMAS_DOC = DOCS_DIR / "04-reference" / "contracts" / "gold-schemas.md"
GOLD_CONTRACTS_DIR = DOCS_DIR / "04-reference" / "contracts" / "gold"
PROVIDERS_OVERVIEW_DOC = DOCS_DIR / "04-reference" / "providers" / "README.md"
CHEMBL_PROVIDERS_DIR = DOCS_DIR / "04-reference" / "providers" / "chembl"
CANONICAL_REQUIREMENTS_FILE = DOCS_DIR / "01-requirements" / "REQUIREMENTS.md"
CANONICAL_GOVERNANCE_DIR = DOCS_DIR / "00-project" / "governance"
NOT_IN_NAV_BASELINE_FILE = (
    PROJECT_ROOT / "scripts" / "baselines" / "not_in_nav_baseline.txt"
)

# Directories to skip in full-tree checks.
# NOTE: docs published in mkdocs nav are always included in link checks
# even if they live under a skipped directory.
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
        "site",
        "99-archive",
    }
)

# Regex to match markdown relative links: [text](path) — excludes http(s)
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((?!https?://|mailto:)([^)#]+)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MD_PATH_RE = re.compile(r"[A-Za-z0-9_./-]+\.md")
PYTHON_FENCE_START_RE = re.compile(r"^\s*```(?:python|py|python3)\b", re.IGNORECASE)
FENCE_END_RE = re.compile(r"^\s*```")
GOLD_CONTRACT_RE = re.compile(r"`([a-z0-9_]+_v1\.0\.json)`")
CHEMBL_PROVIDER_LINK_RE = re.compile(r"\(chembl/([a-z0-9-]+)\.md\)")
GENERATED_EXPORT_MERGED_RE = re.compile(r"^exports/.+\.merged\.md$")
GENERATED_DOCS_EXPORT_REPORT_RE = re.compile(
    r"^reports/docs-export-report-\d{4}-\d{2}-\d{2}-\d{6}\.md$"
)

# Directories skipped by default for drift guardrails in nav docs.
# These sections are mostly historical/internal and can be audited with
# `--legacy-paths-all`.
DRIFT_SKIP_DIRS = frozenset({"99-archive", "reports", "plans", "skills"})

# Optional inline marker to allow historical legacy examples in a specific line.
ALLOW_LEGACY_MARKER = "doc-lint: allow-legacy"


class DriftRule:
    """Rule definition for doc drift detection."""

    def __init__(self, name: str, pattern: re.Pattern[str]) -> None:
        """Initialize drift rule."""
        self.name = name
        self.pattern = pattern


DRIFT_RULES = (
    DriftRule(
        name="legacy_delta_log_token",
        pattern=re.compile(r"(?<![A-Za-z0-9_])(?:-delta-log|delta-log)(?![A-Za-z0-9_])"),
    ),
    DriftRule(
        name="legacy_config_path",
        pattern=re.compile(r"configs/(?:pipelines|sources|schemas|hash-policy)/"),
    ),
    DriftRule(
        name="legacy_script_path",
        pattern=re.compile(r"scripts/validate-pipeline-configs\.py"),
    ),
    DriftRule(
        name="old_run_syntax",
        pattern=re.compile(
            r"\bbioetl\s+run\s+(?!--pipeline\b)([A-Za-z0-9_][A-Za-z0-9_-]*)"
        ),
    ),
    DriftRule(
        name="removed_run_flag",
        pattern=re.compile(r"--(?:input-filter|start-date|end-date|batch-size)\b"),
    ),
    DriftRule(
        name="legacy_run_type_flag",
        pattern=re.compile(r"--run_type\b"),
    ),
    DriftRule(
        name="legacy_system_meta_field_token",
        pattern=re.compile(
            r"(?<![A-Za-z0-9_-])-"
            r"(?:run-id|run-type|source-batch-id|ingestion-ts)"
            r"(?![A-Za-z0-9_-])"
        ),
    ),
    DriftRule(
        name="legacy_lineage_log_token",
        pattern=re.compile(r"\b(?:sys\.)?lineage-log\b"),
    ),
    DriftRule(
        name="legacy_docs_pipelines_path",
        pattern=re.compile(r"docs/pipelines/"),
    ),
    DriftRule(
        name="invalid_env_style",
        pattern=re.compile(r"\bBIOETL-[A-Z][A-Z0-9-]*\b"),
    ),
)

PYTHON_SNIPPET_RULES = (
    DriftRule(
        name="python_renamed_file_token",
        pattern=re.compile(
            r"\b(?:config-loader|dq-config-loader|postrun-service|retention-manager|validate-pipeline-configs|fetch-strategies)\.py\b"
        ),
    ),
    DriftRule(
        name="python_invalid_from_cid_token",
        pattern=re.compile(r"\.from-cid\b"),
    ),
    DriftRule(
        name="python_invalid_get_compounds_token",
        pattern=re.compile(r"\bget-compounds\s*\("),
    ),
    DriftRule(
        name="python_invalid_run_in_executor_token",
        pattern=re.compile(r"\._run-in-executor\b"),
    ),
)


def _should_skip(path: Path) -> bool:
    """Return True if path should be excluded from scanning."""
    if _is_generated_docs_artifact(path):
        return True
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False


def _is_generated_docs_artifact(path: Path, root: Path = DOCS_DIR) -> bool:
    """Return True for generated docs artifacts excluded from nav-growth checks."""
    rel_path = path.relative_to(root).as_posix()
    rel_parts = Path(rel_path).parts
    if bool(rel_parts) and rel_parts[0] == "site":
        return True
    if GENERATED_EXPORT_MERGED_RE.match(rel_path):
        return True
    return bool(GENERATED_DOCS_EXPORT_REPORT_RE.match(rel_path))


def _should_skip_drift(path: Path) -> bool:
    """Return True if path should be excluded from drift guardrails."""
    for part in path.parts:
        if part in DRIFT_SKIP_DIRS:
            return True
    return False


def _iter_python_fence_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Return (line_no, line) entries for fenced python code blocks."""
    in_python_fence = False
    python_lines: list[tuple[int, str]] = []

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not in_python_fence and PYTHON_FENCE_START_RE.match(stripped):
            in_python_fence = True
            continue
        if in_python_fence and FENCE_END_RE.match(stripped):
            in_python_fence = False
            continue
        if in_python_fence:
            python_lines.append((line_no, line))

    return python_lines


def _check_python_snippet_drift(lines: list[str]) -> list[tuple[int, str, str]]:
    """Find drift violations in fenced python snippets."""
    snippet_violations: list[tuple[int, str, str]] = []

    for line_no, line in _iter_python_fence_lines(lines):
        if ALLOW_LEGACY_MARKER in line:
            continue
        for rule in PYTHON_SNIPPET_RULES:
            match = rule.pattern.search(line)
            if match:
                snippet_violations.append((line_no, rule.name, match.group(0)))

    return snippet_violations


def check_broken_links(root: Path) -> list[tuple[Path, int, str, str]]:
    """Find broken relative markdown links in .md files under root.

    Returns list of (file, line_no, link_text, target_path).
    """
    broken: list[tuple[Path, int, str, str]] = []

    for md_file in _collect_link_scan_files(root):

        try:
            lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for line_no, line in enumerate(lines, start=1):
            line_for_links = INLINE_CODE_RE.sub("", line)
            for match in MD_LINK_RE.finditer(line_for_links):
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


def _collect_link_scan_files(root: Path) -> list[Path]:
    """Collect files for link checks: active tree + all existing nav docs."""
    tree_docs = {path.resolve() for path in root.rglob("*.md") if not _should_skip(path)}
    nav_docs = {path.resolve() for path in _load_nav_docs() if path.exists()}
    return sorted(tree_docs | nav_docs)


def check_missing_nav_docs() -> list[Path]:
    """Return nav docs that do not exist on disk."""
    return sorted(path for path in _load_nav_docs() if not path.exists())


def check_nav_link_coverage(root: Path) -> list[Path]:
    """Return nav docs that are unexpectedly outside link check scope."""
    nav_docs = {path.resolve() for path in _load_nav_docs() if path.exists()}
    scan_scope = set(_collect_link_scan_files(root))
    return sorted(nav_docs - scan_scope)


def get_not_in_nav_docs(root: Path = DOCS_DIR) -> list[str]:
    """Return markdown docs that exist on disk but are absent from mkdocs nav."""
    all_docs = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.md")
        if path.is_file() and not _is_generated_docs_artifact(path, root)
    }
    nav_docs = {
        path.relative_to(DOCS_DIR).as_posix()
        for path in _load_nav_docs()
        if path.exists() and DOCS_DIR in path.parents
    }
    return sorted(all_docs - nav_docs)


def _load_not_in_nav_baseline(
    baseline_file: Path = NOT_IN_NAV_BASELINE_FILE,
) -> tuple[set[str], bool]:
    """Load baseline entries for docs intentionally outside mkdocs nav."""
    if not baseline_file.exists():
        return set(), False

    lines = baseline_file.read_text(encoding="utf-8", errors="replace").splitlines()
    entries = {
        line.strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    }
    return entries, True


def check_not_in_nav_growth(
    root: Path = DOCS_DIR,
    baseline_file: Path = NOT_IN_NAV_BASELINE_FILE,
) -> tuple[int, int, list[str], list[str], bool]:
    """Compare current not-in-nav docs against baseline.

    Returns:
        current_count: Current number of docs outside mkdocs nav.
        baseline_count: Baseline number of docs outside mkdocs nav.
        added: Docs present now but absent in baseline.
        removed: Docs present in baseline but absent now.
        baseline_exists: Whether baseline file exists.
    """
    current = set(get_not_in_nav_docs(root))
    baseline, baseline_exists = _load_not_in_nav_baseline(baseline_file)
    added = sorted(current - baseline)
    removed = sorted(baseline - current)
    return len(current), len(baseline), added, removed, baseline_exists


def check_legacy_paths_in_nav_docs(
    include_internal: bool = False,
) -> list[tuple[Path, int, str, str]]:
    """Find doc drift violations in active docs (mkdocs nav)."""
    violations: list[tuple[Path, int, str, str]] = []

    for md_file in _load_nav_docs():
        if not md_file.exists():
            continue
        if not include_internal and _should_skip_drift(md_file):
            continue

        lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(lines, start=1):
            if ALLOW_LEGACY_MARKER in line:
                continue
            for rule in DRIFT_RULES:
                match = rule.pattern.search(line)
                if match:
                    matched_text = match.group(0)
                    violations.append((md_file, line_no, rule.name, matched_text))

        for line_no, rule_name, matched_text in _check_python_snippet_drift(lines):
            violations.append((md_file, line_no, rule_name, matched_text))

        for line_no, rule_name, matched_text in _check_path_contracts_for_file(
            md_file, lines
        ):
            violations.append((md_file, line_no, rule_name, matched_text))

    return violations


def _check_path_contracts_for_file(
    source_file: Path,
    lines: list[str],
) -> list[tuple[int, str, str]]:
    """Check canonical path contracts for REQUIREMENTS and governance docs."""
    docs_root = DOCS_DIR.resolve()
    canonical_requirements = CANONICAL_REQUIREMENTS_FILE.resolve()
    canonical_governance = CANONICAL_GOVERNANCE_DIR.resolve()
    violations: list[tuple[int, str, str]] = []

    for line_no, line in enumerate(lines, start=1):
        line_for_links = INLINE_CODE_RE.sub("", line)
        for match in MD_LINK_RE.finditer(line_for_links):
            raw_target = match.group(2).strip()
            if not raw_target or raw_target.startswith("*") or raw_target.startswith("{"):
                continue

            resolved = (source_file.parent / raw_target).resolve()
            normalized_target = raw_target.replace("\\", "/")

            if (
                resolved.name == "REQUIREMENTS.md"
                and resolved != canonical_requirements
            ):
                violations.append(
                    (
                        line_no,
                        "requirements_path_contract",
                        normalized_target,
                    )
                )

            if not re.search(r"(^|/)governance/", normalized_target):
                continue

            try:
                _ = resolved.relative_to(canonical_governance)
            except ValueError:
                if docs_root in resolved.parents:
                    violations.append(
                        (
                            line_no,
                            "governance_path_contract",
                            normalized_target,
                        )
                    )

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


def check_gold_contract_index() -> tuple[list[str], list[str]]:
    """Compare gold-schemas.md contract list with exported contract JSON files.

    Returns:
        missing_in_doc: Contract JSON files that exist on disk but are not listed.
        extra_in_doc: Contract JSON entries listed in docs but not present on disk.
    """
    if not GOLD_SCHEMAS_DOC.exists() or not GOLD_CONTRACTS_DIR.exists():
        return [], []

    documented = set(
        GOLD_CONTRACT_RE.findall(
            GOLD_SCHEMAS_DOC.read_text(encoding="utf-8", errors="replace")
        )
    )
    exported = {path.name for path in GOLD_CONTRACTS_DIR.glob("*.json")}

    missing_in_doc = sorted(exported - documented)
    extra_in_doc = sorted(documented - exported)
    return missing_in_doc, extra_in_doc


def check_chembl_provider_overview() -> tuple[list[str], list[str]]:
    """Compare ChEMBL overview links in providers README to provider docs inventory.

    Returns:
        missing_in_readme: Provider docs present on disk but absent in README links.
        extra_in_readme: README links that have no matching provider doc.
    """
    if not PROVIDERS_OVERVIEW_DOC.exists() or not CHEMBL_PROVIDERS_DIR.exists():
        return [], []

    readme_text = PROVIDERS_OVERVIEW_DOC.read_text(encoding="utf-8", errors="replace")
    listed = set(CHEMBL_PROVIDER_LINK_RE.findall(readme_text))
    available = {path.stem for path in CHEMBL_PROVIDERS_DIR.glob("*.md")}

    missing_in_readme = sorted(available - listed)
    extra_in_readme = sorted(listed - available)
    return missing_in_readme, extra_in_readme


def main() -> int:
    parser = argparse.ArgumentParser(description="Check documentation links and spec files")
    parser.add_argument("--links", action="store_true", help="Only check broken links")
    parser.add_argument("--specs", action="store_true", help="Only check spec files")
    parser.add_argument("--configs", action="store_true", help="Only check config existence")
    parser.add_argument(
        "--contracts-index",
        action="store_true",
        help="Only check Gold contract index parity (gold-schemas.md vs JSON exports)",
    )
    parser.add_argument(
        "--provider-overview",
        action="store_true",
        help="Only check provider overview parity (providers README vs docs inventory)",
    )
    parser.add_argument(
        "--not-in-nav-growth",
        action="store_true",
        help="Only check growth of markdown docs outside mkdocs nav baseline",
    )
    parser.add_argument(
        "--legacy-paths",
        action="store_true",
        help="Only check doc drift guardrails in mkdocs nav docs",
    )
    parser.add_argument(
        "--legacy-paths-all",
        action="store_true",
        help="Only check doc drift guardrails in all mkdocs nav docs, including internal sections",
    )
    args = parser.parse_args()

    # Default: run all checks
    run_all = not (
        args.links
        or args.specs
        or args.configs
        or args.contracts_index
        or args.provider_overview
        or args.not_in_nav_growth
        or args.legacy_paths
        or args.legacy_paths_all
    )
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

        missing_nav_docs = check_missing_nav_docs()
        if missing_nav_docs:
            print(f"\n{'='*60}")
            print(f"MISSING NAV DOCS ({len(missing_nav_docs)} found)")
            print(f"{'='*60}")
            for filepath in missing_nav_docs:
                rel = filepath.relative_to(PROJECT_ROOT)
                print(f"  {rel}")
            violations += len(missing_nav_docs)
        else:
            print("Nav docs: OK (all mkdocs nav files exist)")

        nav_scope_gaps = check_nav_link_coverage(DOCS_DIR)
        if nav_scope_gaps:
            print(f"\n{'='*60}")
            print(f"NAV LINK SCOPE GAPS ({len(nav_scope_gaps)} found)")
            print(f"{'='*60}")
            for filepath in nav_scope_gaps:
                rel = filepath.relative_to(PROJECT_ROOT)
                print(f"  {rel}")
            violations += len(nav_scope_gaps)
        else:
            print("Nav link scope: OK (all nav docs are included in link checks)")

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

    if run_all or args.contracts_index:
        missing_in_doc, extra_in_doc = check_gold_contract_index()
        if missing_in_doc or extra_in_doc:
            print(f"\n{'='*60}")
            print("GOLD CONTRACT INDEX MISMATCH")
            print(f"{'='*60}")
            if missing_in_doc:
                print("  Missing in docs/04-reference/contracts/gold-schemas.md:")
                for item in missing_in_doc:
                    print(f"    - {item}")
            if extra_in_doc:
                print("  Listed in docs but missing on disk:")
                for item in extra_in_doc:
                    print(f"    - {item}")
            violations += len(missing_in_doc) + len(extra_in_doc)
        else:
            print("Gold contracts index: OK (docs list matches exported JSON files)")

    if run_all or args.provider_overview:
        missing_in_readme, extra_in_readme = check_chembl_provider_overview()
        if missing_in_readme or extra_in_readme:
            print(f"\n{'='*60}")
            print("CHEMBL PROVIDER OVERVIEW MISMATCH")
            print(f"{'='*60}")
            if missing_in_readme:
                print("  Missing in docs/04-reference/providers/README.md:")
                for item in missing_in_readme:
                    print(f"    - chembl/{item}.md")
            if extra_in_readme:
                print("  Linked in README but missing on disk:")
                for item in extra_in_readme:
                    print(f"    - chembl/{item}.md")
            violations += len(missing_in_readme) + len(extra_in_readme)
        else:
            print("ChEMBL provider overview: OK (README links match provider docs)")

    if run_all or args.not_in_nav_growth:
        current_count, baseline_count, added, removed, baseline_exists = (
            check_not_in_nav_growth()
        )
        if not baseline_exists:
            print(f"\n{'='*60}")
            print("NOT IN NAV BASELINE MISSING")
            print(f"{'='*60}")
            rel = NOT_IN_NAV_BASELINE_FILE.relative_to(PROJECT_ROOT)
            print(f"  Missing baseline file: {rel}")
            print(f"  Current not-in-nav docs: {current_count}")
            violations += 1
        elif current_count > baseline_count:
            growth = current_count - baseline_count
            print(f"\n{'='*60}")
            print(f"NOT IN NAV GROWTH (+{growth})")
            print(f"{'='*60}")
            print(f"  baseline: {baseline_count}")
            print(f"  current:  {current_count}")
            if added:
                print("  Added docs outside nav (sample):")
                for rel_path in added[:30]:
                    print(f"    - {rel_path}")
                if len(added) > 30:
                    print(f"    ... and {len(added) - 30} more")
            violations += growth
        else:
            print(
                "Not-in-nav growth: OK "
                f"(current {current_count} <= baseline {baseline_count})"
            )
            if added and removed:
                print(
                    "Not-in-nav set changed without growth "
                    f"(added={len(added)}, removed={len(removed)})"
                )

    if run_all or args.legacy_paths or args.legacy_paths_all:
        legacy_hits = check_legacy_paths_in_nav_docs(
            include_internal=args.legacy_paths_all
        )
        if legacy_hits:
            print(f"\n{'='*60}")
            print(f"DOC DRIFT VIOLATIONS ({len(legacy_hits)} found)")
            print(f"{'='*60}")
            for filepath, line_no, rule_name, matched_text in legacy_hits:
                rel = filepath.relative_to(PROJECT_ROOT)
                print(
                    f"  {rel}:{line_no}: [{rule_name}] contains '{matched_text}'"
                )
            violations += len(legacy_hits)
        else:
            print("Doc drift: OK (no guardrail violations in mkdocs nav docs)")

    if violations:
        print(f"\nTotal violations: {violations}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
