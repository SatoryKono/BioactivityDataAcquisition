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
  7. Provider specs contain required API governance sections
  8. Runbooks contain required operational sections
  9. Published control-plane contract specs contain required contract sections
 10. Provider specs / runbooks / published control-plane contracts contain
     required governance metadata
 11. Version frontmatter uses SemVer format
 12. Local skill mirror pages are explicitly classified via mkdocs `nav` or
     `not_in_nav`

Usage:
    python scripts/check_doc_links.py          # Full check
    python scripts/check_doc_links.py --specs   # Only spec file check
    python scripts/check_doc_links.py --links   # Only broken link check
    python scripts/check_doc_links.py --contracts-index  # Gold contract index parity
    python scripts/check_doc_links.py --provider-overview  # Provider overview parity
    python scripts/check_doc_links.py --doc-governance  # Provider/runbook/control-plane governance checks
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
import os
import re
import sys
from fnmatch import fnmatch
from functools import cache
from pathlib import Path

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import ensure_repo_imports
else:
    from scripts.docs.checks._bootstrap import ensure_repo_imports

ensure_repo_imports()

from scripts.docs.common.markdown import (
    FENCE_END_RE,
    INLINE_CODE_RE,
    MD_LINK_RE,
    MD_PATH_RE,
    PYTHON_FENCE_START_RE,
    extract_md_heading,
)
from scripts.docs.common.paths import DOCS_DIR, PROJECT_ROOT, is_generated_docs_artifact

README_FILENAME = "README.md"
LAST_VERIFIED_LABEL = "Last verified"

PIPELINES_DIR = DOCS_DIR / "04-reference" / "pipelines"
GOLD_SCHEMAS_DOC = DOCS_DIR / "04-reference" / "contracts" / "gold-schemas.md"
GOLD_CONTRACTS_DIR = DOCS_DIR / "04-reference" / "contracts" / "gold"
CONTRACTS_DOC_DIR = DOCS_DIR / "04-reference" / "contracts"
PROVIDERS_OVERVIEW_DOC = DOCS_DIR / "04-reference" / "providers" / README_FILENAME
PROVIDERS_SPECS_DIR = DOCS_DIR / "04-reference" / "providers"
CHEMBL_PROVIDERS_DIR = DOCS_DIR / "04-reference" / "providers" / "chembl"
RUNBOOKS_DIR = DOCS_DIR / "05-operations" / "runbooks"
CANONICAL_REQUIREMENTS_FILE = DOCS_DIR / "01-requirements" / "REQUIREMENTS.md"
CANONICAL_GOVERNANCE_DIR = DOCS_DIR / "00-project" / "governance"
NOT_IN_NAV_BASELINE_FILE = (
    PROJECT_ROOT / "scripts" / "engineering" / "baselines" / "not_in_nav_baseline.txt"
)
LOCAL_SKILLS_DIR = DOCS_DIR / "00-project" / "ai" / "skills" / "local"

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
        "plans",
        "reports",
        "site",
        "99-archive",
    }
)

GOLD_CONTRACT_RE = re.compile(r"`([\w]+_v1\.0\.json)`")
CHEMBL_PROVIDER_LINK_RE = re.compile(r"\(chembl/([a-z0-9-]+)\.md\)")

DRIFT_SKIP_DIRS = frozenset({"99-archive", "reports", "plans", "skills"})
NOT_IN_NAV_GROWTH_EXCLUDED_PREFIXES = ("reports/",)

ALLOW_LEGACY_MARKER = "doc-lint: allow-legacy"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

REQUIRED_PROVIDER_SECTIONS = (
    "API Compliance",
    "Rate limits & retries",
    "429 handling policy",
    "Authentication model",
    "ToS URL",
    "Data license",
    "Personal data notes",
)
REQUIRED_RUNBOOK_SECTIONS = (
    "Trigger",
    "Impact",
    "Preconditions",
    "Procedure",
    "Verification",
    "Rollback/Recovery",
    "Post-incident",
)
REQUIRED_CONTROL_PLANE_CONTRACT_SECTIONS = (
    "Purpose",
    "Storage layout",
    "Rollout flags",
    "Invariants",
    "Inspection surface",
)
CONTROL_PLANE_COMPATIBILITY_FACADE_PATHS = (
    "src/bioetl/application/services/run_manifest_service.py",
    "src/bioetl/application/services/run_ledger_service.py",
    "src/bioetl/application/services/run_manifest_diagnostics.py",
    "src/bioetl/application/services/run_manifest_inspection_service.py",
)
SECTION_SEPARATOR = "=" * 60
DELIMITED_FRONTMATTER_RE = re.compile(r"_{10,}")
LEGACY_DELTA_LOG_TOKEN_RE = re.compile(r"(?<!\w)(?:-delta-log|delta-log)(?!\w)")


class DriftRule:
    """Rule definition for doc drift detection."""

    def __init__(self, name: str, pattern: re.Pattern[str]) -> None:
        self.name = name
        self.pattern = pattern


DRIFT_RULES = (
    DriftRule(
        name="legacy_delta_log_token",
        pattern=LEGACY_DELTA_LOG_TOKEN_RE,
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
            r"\bbioetl\s+run\s+(?!--pipeline\b)([\w][\w-]*)"
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
    DriftRule(
        name="legacy_quarantine_mark_as_reprocessed_token",
        pattern=re.compile(r"\bQuarantineService\.mark_as_reprocessed\b"),
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
    if _is_generated_docs_artifact(path):
        return True
    return any(part in SKIP_DIRS for part in path.parts)


def _is_generated_docs_artifact(path: Path, root: Path = DOCS_DIR) -> bool:
    return is_generated_docs_artifact(path, docs_root=root)


def _should_skip_drift(path: Path) -> bool:
    return any(part in DRIFT_SKIP_DIRS for part in path.parts)


def _iter_python_fence_lines(lines: list[str]) -> list[tuple[int, str]]:
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
    snippet_violations: list[tuple[int, str, str]] = []

    for line_no, line in _iter_python_fence_lines(lines):
        if ALLOW_LEGACY_MARKER in line:
            continue
        for rule in PYTHON_SNIPPET_RULES:
            match = rule.pattern.search(line)
            if match:
                snippet_violations.append((line_no, rule.name, match.group(0)))

    return snippet_violations


def _extract_delimited_header_frontmatter(text: str) -> dict[str, object]:
    lines = text.splitlines()
    start_index = 0
    while start_index < len(lines) and not lines[start_index].strip():
        start_index += 1

    if start_index >= len(lines) or not DELIMITED_FRONTMATTER_RE.fullmatch(
        lines[start_index]
    ):
        return {}

    end_index = _find_frontmatter_delimiter_end(lines, start_index + 1)
    if end_index >= len(lines):
        return {}

    metadata_lines = lines[start_index + 1 : end_index]
    frontmatter: dict[str, object] = {}
    current_key: str | None = None

    for raw_line in metadata_lines:
        current_key = _update_delimited_frontmatter(frontmatter, raw_line, current_key)

    return frontmatter


def _find_frontmatter_delimiter_end(lines: list[str], start_index: int) -> int:
    end_index = start_index
    while end_index < len(lines) and not DELIMITED_FRONTMATTER_RE.fullmatch(
        lines[end_index]
    ):
        end_index += 1
    return end_index


def _update_delimited_frontmatter(
    frontmatter: dict[str, object],
    raw_line: str,
    current_key: str | None,
) -> str | None:
    stripped = raw_line.strip()
    if not stripped:
        return current_key

    nested_entry = _parse_frontmatter_line(raw_line, require_indent=True)
    if nested_entry is not None:
        key, value = nested_entry
        frontmatter[key] = value
        return current_key

    key_value_entry = _parse_frontmatter_line(raw_line, require_indent=False)
    if key_value_entry is not None:
        current_key, value = key_value_entry
        frontmatter[current_key] = value
        return current_key

    if current_key == "Reviewers" and stripped.startswith("- "):
        reviewers = frontmatter.setdefault("Reviewers", [])
        if isinstance(reviewers, list):
            reviewers.append(stripped[2:].strip())

    return current_key


def _parse_frontmatter_line(
    raw_line: str,
    *,
    require_indent: bool,
) -> tuple[str, str] | None:
    if require_indent:
        if not raw_line or raw_line[0] not in {" ", "\t"}:
            return None
        candidate = raw_line.lstrip(" \t")
    else:
        if raw_line and raw_line[0] in {" ", "\t"}:
            return None
        candidate = raw_line

    key, separator, value = candidate.partition(":")
    if not separator:
        return None
    key = key.strip()
    if not key:
        return None
    return key, value.strip()


def _extract_frontmatter(md_file: Path) -> dict[str, object]:
    try:
        text = md_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    if not text.startswith("---\n"):
        return _extract_delimited_header_frontmatter(text)

    _, _, remainder = text.partition("---\n")
    frontmatter_text, sep, _ = remainder.partition("\n---")
    if not sep:
        return _extract_delimited_header_frontmatter(text)

    loaded = yaml.safe_load(frontmatter_text)
    if isinstance(loaded, dict):
        return loaded
    return _extract_delimited_header_frontmatter(text)


def _extract_headings(md_file: Path) -> set[str]:
    try:
        lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return set()

    headings: set[str] = set()
    for line in lines:
        heading = extract_md_heading(line)
        if heading is None:
            continue
        headings.add(heading.casefold())
    return headings


def _is_published_doc(frontmatter: dict[str, object]) -> bool:
    raw_class = frontmatter.get("Class")
    return raw_class is not None and str(raw_class).strip().casefold() == "published"


def _has_heading(headings: set[str], section: str) -> bool:
    return section.casefold() in headings


def _has_any_heading(headings: set[str], *sections: str) -> bool:
    return any(_has_heading(headings, section) for section in sections)


def _provider_spec_files() -> list[Path]:
    return sorted(
        path
        for path in PROVIDERS_SPECS_DIR.glob("*/*.md")
        if path.name.lower() != "readme.md"
    )


def _runbook_files() -> list[Path]:
    return sorted(path for path in RUNBOOKS_DIR.glob("*.md") if path.is_file())


def _control_plane_contract_spec_files() -> list[Path]:
    candidates = sorted(
        path
        for path in CONTRACTS_DOC_DIR.glob("*.md")
        if path.is_file() and path.name.lower() not in {"readme.md", "gold-schemas.md"}
    )
    control_plane_files: list[Path] = []
    for md_file in candidates:
        frontmatter = _extract_frontmatter(md_file)
        if not _is_published_doc(frontmatter):
            continue
        stem = md_file.stem.casefold()
        if any(token in stem for token in ("run-manifest", "run-ledger", "control-plane")):
            control_plane_files.append(md_file)
    return control_plane_files


def _append_missing_last_verified_violation(
    violations: list[tuple[Path, str]],
    md_file: Path,
    frontmatter: dict[str, object],
    label: str,
) -> None:
    last_verified = frontmatter.get(LAST_VERIFIED_LABEL)
    if not isinstance(last_verified, str) or not last_verified.strip():
        violations.append((md_file, f"{label}: missing {LAST_VERIFIED_LABEL} frontmatter"))


def _append_invalid_version_violation(
    violations: list[tuple[Path, str]],
    md_file: Path,
    frontmatter: dict[str, object],
    label: str,
) -> None:
    version = frontmatter.get("Version")
    version_str = str(version).strip() if version is not None else ""
    if not SEMVER_RE.fullmatch(version_str):
        violations.append((md_file, f"{label}: invalid Version SemVer: {version_str!r}"))


def _append_governance_metadata_violations(
    violations: list[tuple[Path, str]],
    md_file: Path,
    frontmatter: dict[str, object],
    label: str,
) -> None:
    _append_missing_last_verified_violation(violations, md_file, frontmatter, label)
    _append_invalid_version_violation(violations, md_file, frontmatter, label)


def _append_runbook_section_violations(
    violations: list[tuple[Path, str]],
    md_file: Path,
    headings: set[str],
) -> None:
    for section in REQUIRED_RUNBOOK_SECTIONS:
        if section == "Rollback/Recovery":
            if _has_any_heading(headings, "Rollback", "Recovery"):
                continue
            violations.append((md_file, "runbook: missing required section 'Rollback/Recovery'"))
            continue
        if not _has_heading(headings, section):
            violations.append((md_file, f"runbook: missing required section '{section}'"))


def _append_control_plane_section_violations(
    violations: list[tuple[Path, str]],
    md_file: Path,
    headings: set[str],
) -> None:
    for section in REQUIRED_CONTROL_PLANE_CONTRACT_SECTIONS:
        if section == "Inspection surface":
            if _has_any_heading(headings, "Inspection Surface", "CLI Inspection"):
                continue
            violations.append(
                (md_file, "control-plane contract-spec: missing required section 'Inspection surface'")
            )
            continue
        if not _has_heading(headings, section):
            violations.append(
                (md_file, f"control-plane contract-spec: missing required section '{section}'")
            )


def check_provider_spec_governance() -> list[tuple[Path, str]]:
    violations: list[tuple[Path, str]] = []

    for md_file in _provider_spec_files():
        headings = _extract_headings(md_file)
        frontmatter = _extract_frontmatter(md_file)

        for section in REQUIRED_PROVIDER_SECTIONS:
            if section.casefold() not in headings:
                violations.append(
                    (md_file, f"provider-spec: missing required section '{section}'")
                )

        if "compliance" not in " ".join(headings):
            violations.append((md_file, "provider-spec: missing Compliance heading"))

        _append_governance_metadata_violations(
            violations, md_file, frontmatter, "provider-spec"
        )

    return violations


def check_runbook_governance() -> list[tuple[Path, str]]:
    violations: list[tuple[Path, str]] = []

    for md_file in _runbook_files():
        headings = _extract_headings(md_file)
        frontmatter = _extract_frontmatter(md_file)

        _append_runbook_section_violations(violations, md_file, headings)

        if "compliance" not in " ".join(headings):
            violations.append((md_file, "runbook: missing Compliance heading"))

        _append_governance_metadata_violations(violations, md_file, frontmatter, "runbook")

    return violations


def check_control_plane_contract_governance() -> list[tuple[Path, str]]:
    violations: list[tuple[Path, str]] = []

    for md_file in _control_plane_contract_spec_files():
        headings = _extract_headings(md_file)
        frontmatter = _extract_frontmatter(md_file)

        _append_control_plane_section_violations(violations, md_file, headings)
        _append_governance_metadata_violations(
            violations, md_file, frontmatter, "control-plane contract-spec"
        )

        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for legacy_path in CONTROL_PLANE_COMPATIBILITY_FACADE_PATHS:
            if legacy_path not in text:
                continue
            canonical_path = legacy_path.replace(
                "src/bioetl/application/services/",
                "src/bioetl/application/services/control_plane/",
                1,
            )
            violations.append(
                (
                    md_file,
                    "control-plane contract-spec: compatibility facade path "
                    f"{legacy_path!r} is not sanctioned; use {canonical_path!r}",
                )
            )

    return violations


def _iter_markdown_targets(
    source_file: Path,
    lines: list[str],
) -> list[tuple[int, str, str, str, Path]]:
    targets: list[tuple[int, str, str, str, Path]] = []
    for line_no, line in enumerate(lines, start=1):
        line_for_links = INLINE_CODE_RE.sub("", line)
        for match in MD_LINK_RE.finditer(line_for_links):
            raw_target = match.group(2).strip()
            if not raw_target or raw_target.startswith("*") or raw_target.startswith("{"):
                continue
            targets.append(
                (
                    line_no,
                    match.group(1),
                    raw_target,
                    raw_target.replace("\\", "/"),
                    (source_file.parent / raw_target).resolve(),
                )
            )
    return targets


def check_broken_links(root: Path) -> list[tuple[Path, int, str, str]]:
    broken: list[tuple[Path, int, str, str]] = []

    for md_file in _collect_link_scan_files(root):
        try:
            lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for line_no, link_text, raw_target, _, resolved in _iter_markdown_targets(
            md_file, lines
        ):
            if raw_target.endswith((".png", ".svg")):
                continue
            if not resolved.exists():
                broken.append((md_file, line_no, link_text, raw_target))

    return broken


@cache
def _load_nav_docs() -> list[Path]:
    nav_paths = _load_mkdocs_path_block("nav")
    return [DOCS_DIR / rel_path for rel_path in nav_paths if not rel_path.startswith("/")]


@cache
def _load_mkdocs_path_block(block_name: str) -> list[str]:
    mkdocs_file = PROJECT_ROOT / "mkdocs.yml"
    if not mkdocs_file.exists():
        return []

    raw = mkdocs_file.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    block_lines: list[str] = []
    in_block = False

    for line in lines:
        stripped = line.strip()
        if not in_block:
            if stripped in {f"{block_name}:", f"{block_name}: |", f"{block_name}: |-"}:
                in_block = True
            continue

        if line and not line.startswith((" ", "\t")) and ":" in line:
            break
        if not stripped or stripped.startswith("#"):
            continue
        block_lines.append(line.split(" #")[0] if " #" in line else line)

    return sorted(set(MD_PATH_RE.findall("\n".join(block_lines))))


@cache
def _load_not_in_nav_patterns() -> list[str]:
    return _load_mkdocs_path_block("not_in_nav")


@cache
def _collect_link_scan_files(root: Path) -> list[Path]:
    tree_docs = set(_iter_markdown_files(root))
    nav_docs = set(_load_nav_docs())
    return sorted(tree_docs | nav_docs)


@cache
def _iter_markdown_files(root: Path) -> list[Path]:
    markdown_files: list[Path] = []
    root = root.resolve()

    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        dirnames[:] = [dirname for dirname in dirnames if not _should_skip(current_path / dirname)]

        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            candidate = current_path / filename
            if _should_skip(candidate):
                continue
            markdown_files.append(candidate)

    return markdown_files


def check_missing_nav_docs() -> list[Path]:
    return sorted(path for path in _load_nav_docs() if not path.exists())


def check_nav_link_coverage(root: Path) -> list[Path]:
    nav_docs = {path.resolve() for path in _load_nav_docs() if path.exists()}
    scan_scope = set(_collect_link_scan_files(root))
    return sorted(nav_docs - scan_scope)


def get_not_in_nav_docs(root: Path = DOCS_DIR) -> list[str]:
    all_docs = {
        path.relative_to(root).as_posix()
        for path in _iter_markdown_files(root)
        if path.is_file() and not _is_generated_docs_artifact(path, root)
    }
    nav_docs = {
        path.relative_to(DOCS_DIR).as_posix()
        for path in _load_nav_docs()
        if path.exists() and DOCS_DIR in path.parents
    }
    return sorted(all_docs - nav_docs)


def _filter_not_in_nav_growth_scope(paths: set[str]) -> set[str]:
    return {path for path in paths if not path.startswith(NOT_IN_NAV_GROWTH_EXCLUDED_PREFIXES)}


def _load_not_in_nav_baseline(
    baseline_file: Path = NOT_IN_NAV_BASELINE_FILE,
) -> tuple[set[str], bool]:
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
    current = _filter_not_in_nav_growth_scope(set(get_not_in_nav_docs(root)))
    baseline, baseline_exists = _load_not_in_nav_baseline(baseline_file)
    baseline = _filter_not_in_nav_growth_scope(baseline)
    added = sorted(current - baseline)
    removed = sorted(baseline - current)
    return len(current), len(baseline), added, removed, baseline_exists


def check_local_skill_nav_classification() -> list[str]:
    nav_docs = {
        path.relative_to(DOCS_DIR).as_posix()
        for path in _load_nav_docs()
        if path.exists() and DOCS_DIR in path.parents
    }
    not_in_nav_patterns = _load_not_in_nav_patterns()
    skill_docs = sorted(
        path.relative_to(DOCS_DIR).as_posix()
        for path in LOCAL_SKILLS_DIR.glob("*/SKILL.md")
    )
    return [
        rel_path
        for rel_path in skill_docs
        if rel_path not in nav_docs
        and not any(fnmatch(rel_path, pattern) for pattern in not_in_nav_patterns)
    ]


def check_legacy_paths_in_nav_docs(
    include_internal: bool = False,
) -> list[tuple[Path, int, str, str]]:
    violations: list[tuple[Path, int, str, str]] = []

    for md_file in _load_nav_docs():
        if not md_file.exists():
            continue
        if not include_internal and _should_skip_drift(md_file):
            continue

        lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
        violations.extend(_collect_file_drift_violations(md_file, lines))

    return violations


def _collect_file_drift_violations(
    md_file: Path,
    lines: list[str],
) -> list[tuple[Path, int, str, str]]:
    violations: list[tuple[Path, int, str, str]] = []

    for line_no, line in enumerate(lines, start=1):
        if ALLOW_LEGACY_MARKER in line:
            continue
        for rule in DRIFT_RULES:
            match = rule.pattern.search(line)
            if match:
                violations.append((md_file, line_no, rule.name, match.group(0)))

    violations.extend(
        (md_file, line_no, rule_name, matched_text)
        for line_no, rule_name, matched_text in _check_python_snippet_drift(lines)
    )
    violations.extend(
        (md_file, line_no, rule_name, matched_text)
        for line_no, rule_name, matched_text in _check_path_contracts_for_file(md_file, lines)
    )
    return violations


def _check_path_contracts_for_file(
    source_file: Path,
    lines: list[str],
) -> list[tuple[int, str, str]]:
    docs_root = DOCS_DIR.resolve()
    canonical_requirements = CANONICAL_REQUIREMENTS_FILE.resolve()
    canonical_governance = CANONICAL_GOVERNANCE_DIR.resolve()
    violations: list[tuple[int, str, str]] = []

    for line_no, _, _, normalized_target, resolved in _iter_markdown_targets(
        source_file, lines
    ):
        if resolved.name == "REQUIREMENTS.md" and resolved != canonical_requirements:
            violations.append((line_no, "requirements_path_contract", normalized_target))

        if not re.search(r"(^|/)governance/", normalized_target):
            continue

        try:
            _ = resolved.relative_to(canonical_governance)
        except ValueError:
            if docs_root in resolved.parents:
                violations.append((line_no, "governance_path_contract", normalized_target))

    return violations


def check_spec_files() -> list[tuple[str, str]]:
    readme = PIPELINES_DIR / README_FILENAME
    if not readme.exists():
        return [(README_FILENAME, str(readme))]

    missing: list[tuple[str, str]] = []
    text = readme.read_text(encoding="utf-8", errors="replace")

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
                missing.append((f"{provider}/{entity}", f"configs/entities/{provider}/{entity}.yaml::{section}"))

        provider_config = providers_dir / f"{provider}.yaml"
        if not provider_config.exists():
            missing.append((f"{provider}/{entity}", f"configs/providers/{provider}.yaml"))

    return missing


def check_gold_contract_index() -> tuple[list[str], list[str]]:
    if not GOLD_SCHEMAS_DOC.exists() or not GOLD_CONTRACTS_DIR.exists():
        return [], []

    documented = set(GOLD_CONTRACT_RE.findall(GOLD_SCHEMAS_DOC.read_text(encoding="utf-8", errors="replace")))
    exported = {path.name for path in GOLD_CONTRACTS_DIR.glob("*.json")}

    return sorted(exported - documented), sorted(documented - exported)


def check_chembl_provider_overview() -> tuple[list[str], list[str]]:
    if not PROVIDERS_OVERVIEW_DOC.exists() or not CHEMBL_PROVIDERS_DIR.exists():
        return [], []

    readme_text = PROVIDERS_OVERVIEW_DOC.read_text(encoding="utf-8", errors="replace")
    listed = set(CHEMBL_PROVIDER_LINK_RE.findall(readme_text))
    available = {path.stem for path in CHEMBL_PROVIDERS_DIR.glob("*.md")}

    return sorted(available - listed), sorted(listed - available)


def _build_parser() -> argparse.ArgumentParser:
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
        "--doc-governance",
        action="store_true",
        help=(
            "Only check provider-spec/runbook/control-plane contract sections, "
            "required governance metadata, and Version SemVer"
        ),
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
    return parser


def _print_section_header(title: str) -> None:
    print(f"\n{SECTION_SEPARATOR}")
    print(title)
    print(SECTION_SEPARATOR)


def _print_path_message_violations(
    title: str,
    violations: list[tuple[Path, str]],
) -> int:
    if not violations:
        return 0
    _print_section_header(f"{title} ({len(violations)} found)")
    for filepath, message in violations:
        rel = filepath.relative_to(PROJECT_ROOT)
        print(f"  {rel}: {message}")
    return len(violations)


def _run_links_checks() -> int:
    violations = 0

    broken = check_broken_links(DOCS_DIR)
    if broken:
        _print_section_header(f"BROKEN LINKS ({len(broken)} found)")
        for filepath, line_no, text, target in broken:
            rel = filepath.relative_to(PROJECT_ROOT)
            print(f"  {rel}:{line_no}: [{text}]({target})")
        violations += len(broken)
    else:
        print("Links: OK (no broken relative links found)")

    missing_nav_docs = check_missing_nav_docs()
    if missing_nav_docs:
        _print_section_header(f"MISSING NAV DOCS ({len(missing_nav_docs)} found)")
        for filepath in missing_nav_docs:
            rel = filepath.relative_to(PROJECT_ROOT)
            print(f"  {rel}")
        violations += len(missing_nav_docs)
    else:
        print("Nav docs: OK (all mkdocs nav files exist)")

    nav_scope_gaps = check_nav_link_coverage(DOCS_DIR)
    if nav_scope_gaps:
        _print_section_header(f"NAV LINK SCOPE GAPS ({len(nav_scope_gaps)} found)")
        for filepath in nav_scope_gaps:
            rel = filepath.relative_to(PROJECT_ROOT)
            print(f"  {rel}")
        violations += len(nav_scope_gaps)
    else:
        print("Nav link scope: OK (all nav docs are included in link checks)")

    unclassified_local_skill_docs = check_local_skill_nav_classification()
    if unclassified_local_skill_docs:
        _print_section_header(
            "LOCAL SKILL NAV CLASSIFICATION VIOLATIONS "
            f"({len(unclassified_local_skill_docs)} found)"
        )
        for rel_path in unclassified_local_skill_docs:
            print(f"  docs/{rel_path}")
        print("  Fix by adding the page to mkdocs nav or to mkdocs not_in_nav.")
        violations += len(unclassified_local_skill_docs)
    else:
        print(
            "Local skill nav classification: OK "
            "(all local skill pages are in nav or not_in_nav)"
        )

    return violations


def _run_specs_check() -> int:
    missing_specs = check_spec_files()
    if not missing_specs:
        print("Specs: OK (all referenced spec files exist)")
        return 0

    _print_section_header(f"MISSING SPEC FILES ({len(missing_specs)} found)")
    for label, path in missing_specs:
        print(f"  {label} -> {path}")
    return len(missing_specs)


def _run_configs_check() -> int:
    missing_configs = check_config_existence()
    if not missing_configs:
        print("Configs: OK (all convention-based config files exist)")
        return 0

    _print_section_header(f"MISSING CONFIG FILES ({len(missing_configs)} found)")
    for pipeline, path in missing_configs:
        print(f"  {pipeline} -> {path}")
    return len(missing_configs)


def _run_contracts_index_check() -> int:
    missing_in_doc, extra_in_doc = check_gold_contract_index()
    if not (missing_in_doc or extra_in_doc):
        print("Gold contracts index: OK (docs list matches exported JSON files)")
        return 0

    _print_section_header("GOLD CONTRACT INDEX MISMATCH")
    if missing_in_doc:
        print("  Missing in docs/04-reference/contracts/gold-schemas.md:")
        for item in missing_in_doc:
            print(f"    - {item}")
    if extra_in_doc:
        print("  Listed in docs but missing on disk:")
        for item in extra_in_doc:
            print(f"    - {item}")
    return len(missing_in_doc) + len(extra_in_doc)


def _run_provider_overview_check() -> int:
    missing_in_readme, extra_in_readme = check_chembl_provider_overview()
    if not (missing_in_readme or extra_in_readme):
        print("ChEMBL provider overview: OK (README links match provider docs)")
        return 0

    _print_section_header("CHEMBL PROVIDER OVERVIEW MISMATCH")
    if missing_in_readme:
        print("  Missing in docs/04-reference/providers/README.md:")
        for item in missing_in_readme:
            print(f"    - chembl/{item}.md")
    if extra_in_readme:
        print("  Linked in README but missing on disk:")
        for item in extra_in_readme:
            print(f"    - chembl/{item}.md")
    return len(missing_in_readme) + len(extra_in_readme)


def _run_doc_governance_check() -> int:
    violations = 0
    governance_checks = (
        (
            "PROVIDER SPEC GOVERNANCE VIOLATIONS",
            check_provider_spec_governance(),
            "Provider spec governance: OK",
        ),
        (
            "RUNBOOK GOVERNANCE VIOLATIONS",
            check_runbook_governance(),
            "Runbook governance: OK",
        ),
        (
            "CONTROL-PLANE CONTRACT GOVERNANCE VIOLATIONS",
            check_control_plane_contract_governance(),
            "Control-plane contract governance: OK",
        ),
    )

    for title, results, ok_message in governance_checks:
        count = _print_path_message_violations(title, results)
        if count:
            violations += count
            continue
        print(ok_message)

    return violations


def _run_not_in_nav_growth_check() -> int:
    current_count, baseline_count, added, removed, baseline_exists = check_not_in_nav_growth()
    if not baseline_exists:
        _print_section_header("NOT IN NAV BASELINE MISSING")
        rel = NOT_IN_NAV_BASELINE_FILE.relative_to(PROJECT_ROOT)
        print(f"  Missing baseline file: {rel}")
        print(f"  Current not-in-nav docs: {current_count}")
        return 1

    if current_count > baseline_count:
        growth = current_count - baseline_count
        _print_section_header(f"NOT IN NAV GROWTH (+{growth})")
        print(f"  baseline: {baseline_count}")
        print(f"  current:  {current_count}")
        if added:
            print("  Added docs outside nav (sample):")
            for rel_path in added[:30]:
                print(f"    - {rel_path}")
            if len(added) > 30:
                print(f"    ... and {len(added) - 30} more")
        return growth

    print(
        "Not-in-nav growth: OK "
        f"(current {current_count} <= baseline {baseline_count})"
    )
    if added and removed:
        print(
            "Not-in-nav set changed without growth "
            f"(added={len(added)}, removed={len(removed)})"
        )
    return 0


def _run_legacy_paths_check(include_internal: bool) -> int:
    legacy_hits = check_legacy_paths_in_nav_docs(include_internal=include_internal)
    if not legacy_hits:
        print("Doc drift: OK (no guardrail violations in mkdocs nav docs)")
        return 0

    _print_section_header(f"DOC DRIFT VIOLATIONS ({len(legacy_hits)} found)")
    for filepath, line_no, rule_name, matched_text in legacy_hits:
        rel = filepath.relative_to(PROJECT_ROOT)
        print(f"  {rel}:{line_no}: [{rule_name}] contains '{matched_text}'")
    return len(legacy_hits)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    explicit_checks = (
        args.links
        or args.specs
        or args.configs
        or args.contracts_index
        or args.provider_overview
        or args.doc_governance
        or args.not_in_nav_growth
        or args.legacy_paths
        or args.legacy_paths_all
    )
    run_all = not explicit_checks
    violations = 0

    check_runners = (
        (run_all or args.links, lambda: _run_links_checks()),
        (run_all or args.specs, lambda: _run_specs_check()),
        (run_all or args.configs, lambda: _run_configs_check()),
        (run_all or args.contracts_index, lambda: _run_contracts_index_check()),
        (run_all or args.provider_overview, lambda: _run_provider_overview_check()),
        (run_all or args.doc_governance, lambda: _run_doc_governance_check()),
        (run_all or args.not_in_nav_growth, lambda: _run_not_in_nav_growth_check()),
        (
            run_all or args.legacy_paths or args.legacy_paths_all,
            lambda: _run_legacy_paths_check(include_internal=args.legacy_paths_all),
        ),
    )

    for should_run, runner in check_runners:
        if should_run:
            violations += runner()

    if violations:
        print(f"\nTotal violations: {violations}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
