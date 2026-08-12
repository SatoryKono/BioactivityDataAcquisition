# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

import pytest

from collections import Counter
import re
from pathlib import Path

import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = PROJECT_ROOT / "docs"
CONFIGS_ROOT = PROJECT_ROOT / "configs"
ENTITIES_DIR = CONFIGS_ROOT / "entities"
ACTIVE_DOC_EXCLUDED_PARTS = frozenset({"99-archive", "exports", "reports", "generated"})
GENERATED_EXPORT_MERGED_RE = re.compile(r"^exports/.+\.merged\.md$")
GENERATED_DOCS_EXPORT_REPORT_RE = re.compile(
    r"^reports/docs-export-report-\d{4}-\d{2}-\d{2}-\d{6}\.md$"
)
GENERATED_PASSPORT_MARKDOWN_RE = re.compile(
    r"^04-reference/passports/(?:index\.md|(?:pipelines|workflows)/.+\.md)$"
)
CANONICAL_DOC_ROOTS = (
    DOCS_ROOT / "02-architecture",
    DOCS_ROOT / "03-guides",
    DOCS_ROOT / "04-reference",
)


def test_codeowners_assigns_explicit_docs_ownership() -> None:
    """Published docs roots must have explicit review ownership."""
    codeowners = (PROJECT_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")

    assert "docs/00-project/ @SatoryKono" in codeowners
    assert "docs/02-architecture/ @SatoryKono" in codeowners


def _resolve_composite_config_dir() -> Path:
    return CONFIGS_ROOT / "composites"


def _is_generated_docs_artifact(path: Path, docs_root: Path = DOCS_ROOT) -> bool:
    """Return True for generated docs artifacts excluded from active sync checks."""
    rel_path = path.relative_to(docs_root).as_posix()
    rel_parts = Path(rel_path).parts
    if bool(rel_parts) and rel_parts[0] == "site":
        return True
    if GENERATED_EXPORT_MERGED_RE.match(rel_path):
        return True
    if GENERATED_PASSPORT_MARKDOWN_RE.match(rel_path):
        return True
    return bool(GENERATED_DOCS_EXPORT_REPORT_RE.match(rel_path))


def _iter_active_docs_markdown(docs_markdown_files: list[Path]) -> list[Path]:
    """Collect markdown docs included in active docs sync scope."""
    return sorted(
        path
        for path in docs_markdown_files
        if ACTIVE_DOC_EXCLUDED_PARTS.isdisjoint(path.parts)
        and not _is_generated_docs_artifact(path, DOCS_ROOT)
    )


def _iter_generated_docs_markdown(docs_markdown_files: list[Path]) -> list[Path]:
    """Collect generated markdown docs tracked by dedicated generated-docs gates."""
    return sorted(
        path
        for path in docs_markdown_files
        if _is_generated_docs_artifact(path, DOCS_ROOT)
    )


def _iter_report_docs_markdown(docs_markdown_files: list[Path]) -> list[Path]:
    """Collect dated/internal report docs excluded from active sync scope."""
    reports_dir = DOCS_ROOT / "reports"
    if not reports_dir.exists():
        return []
    return sorted(path for path in docs_markdown_files if reports_dir in path.parents)


def _iter_generated_zone_markdown(docs_markdown_files: list[Path]) -> list[Path]:
    """Collect markdown from generated documentation zones."""
    generated_dir = DOCS_ROOT / "02-architecture" / "generated"
    zone_docs = [
        path
        for path in docs_markdown_files
        if generated_dir.exists() and generated_dir in path.parents
    ]
    return sorted({*zone_docs, *_iter_generated_docs_markdown(docs_markdown_files)})


def _iter_canonical_docs_markdown(docs_markdown_files: list[Path]) -> list[Path]:
    """Collect canonical active docs under architecture/guides/reference roots."""
    return sorted(
        path
        for path in docs_markdown_files
        if any(
            root == path.parent or root in path.parents for root in CANONICAL_DOC_ROOTS
        )
        and ACTIVE_DOC_EXCLUDED_PARTS.isdisjoint(path.parts)
        and not _is_generated_docs_artifact(path)
    )


def _iter_standard_pipeline_ids(
    *,
    config_yaml_files: list[Path],
    config_text_cache: dict[Path, str],
) -> list[str]:
    provider_ids: list[str] = []
    for path in sorted(config_yaml_files):
        pipeline_name = _extract_standard_pipeline_id(
            path=path,
            config_text_cache=config_text_cache,
        )
        if pipeline_name is not None:
            provider_ids.append(pipeline_name)
    return provider_ids


def _extract_standard_pipeline_id(
    *,
    path: Path,
    config_text_cache: dict[Path, str],
) -> str | None:
    if ENTITIES_DIR not in path.parents or path.name in {"_base.yaml", "_schema.json"}:
        return None
    raw = yaml.safe_load(config_text_cache[path]) or {}
    if not isinstance(raw, dict):
        return None
    pipeline = raw.get("pipeline")
    if not isinstance(pipeline, dict):
        return None
    pipeline_name = pipeline.get("pipeline_name")
    return pipeline_name if isinstance(pipeline_name, str) else None


def _iter_composite_pipeline_ids(
    *,
    composite_dir: Path,
    config_text_cache: dict[Path, str],
) -> list[str]:
    composite_ids: list[str] = []
    for path in sorted(composite_dir.glob("*.yaml")):
        pipeline_id = _extract_composite_pipeline_id(
            path=path,
            config_text_cache=config_text_cache,
        )
        if pipeline_id is not None:
            composite_ids.append(pipeline_id)
    return composite_ids


def _extract_composite_pipeline_id(
    *,
    path: Path,
    config_text_cache: dict[Path, str],
) -> str | None:
    text = config_text_cache.get(path, path.read_text(encoding="utf-8"))
    match = re.search(
        r"^\s*name:\s*(composite_[a-z0-9_]+)\s*$", text, flags=re.MULTILINE
    )
    return match.group(1) if match is not None else None


def _extract_documented_pipeline_ids(reference_text: str) -> list[str]:
    return sorted(
        set(
            re.findall(
                r"\|\s*\d+\s*\|\s*`([a-z0-9_]+)`\s*\|",
                reference_text,
                flags=re.MULTILINE,
            )
        )
    )


def _extract_adr_status(text: str) -> str | None:
    labels = ("status", "статус")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        inline_status = _extract_inline_adr_status(stripped, labels)
        if inline_status is not None:
            return inline_status
        if not stripped.startswith("|"):
            continue
        table_status = _extract_table_adr_status(stripped, labels)
        if table_status is not None:
            return table_status
    return None


def _extract_inline_adr_status(
    stripped: str,
    labels: tuple[str, ...],
) -> str | None:
    lowered = stripped.casefold()
    for label in labels:
        prefixes = (
            f"**{label}:**",
            f"* **{label}**:",
            f"{label}:",
        )
        for prefix in prefixes:
            if lowered.startswith(prefix.casefold()):
                value = stripped[len(prefix) :].strip()
                return value or None
    return None


def _extract_table_adr_status(
    stripped: str,
    labels: tuple[str, ...],
) -> str | None:
    cells = [cell.strip() for cell in stripped.split("|") if cell.strip()]
    if len(cells) < 2:
        return None
    header = cells[0].strip("* ").casefold()
    if header in labels and cells[1]:
        return cells[1]
    return None


def _normalize_adr_status(raw_status: str) -> str:
    return re.split(r"[\s(]", raw_status, maxsplit=1)[0].strip().lower()


def _iter_adr_status_violations(
    *,
    decisions_dir: Path,
    allowed_statuses: set[str],
) -> list[str]:
    violations: list[str] = []
    for path in sorted(decisions_dir.glob("ADR-*.md")):
        raw_status = _extract_adr_status(path.read_text(encoding="utf-8"))
        if raw_status is None:
            violations.append(f"{path.name}: missing status field")
            continue
        normalized = _normalize_adr_status(raw_status)
        if normalized not in allowed_statuses:
            violations.append(
                f"{path.name}: invalid status '{raw_status}' "
                f"(allowed: {sorted(allowed_statuses)})"
            )
    return violations


def test_ports_count_matches_docs() -> None:
    actual = len(list(Path("src/bioetl/domain/ports").glob("*.py")))
    text = Path("docs/02-architecture/01-domain-layer.md").read_text(encoding="utf-8")
    assert str(actual) in text, (
        f"Ports count {actual} not reflected in docs/02-architecture/01-domain-layer.md"
    )


def test_pipeline_count_matches_docs(config_yaml_files: list[Path]) -> None:
    composite_dir = _resolve_composite_config_dir()
    standard = [
        p
        for p in config_yaml_files
        if ENTITIES_DIR in p.parents
        if p.name not in {"_base.yaml", "_schema.json"}
    ]
    composite = list(composite_dir.glob("*.yaml"))
    text = Path("docs/04-reference/pipelines/README.md").read_text(encoding="utf-8")
    assert str(len(standard)) in text and str(len(composite)) in text


def test_pipeline_ids_match_reference_index(
    config_yaml_files: list[Path],
    config_text_cache: dict[Path, str],
) -> None:
    """Pipeline IDs in reference index must match config-defined IDs."""
    composite_dir = _resolve_composite_config_dir()
    provider_ids = _iter_standard_pipeline_ids(
        config_yaml_files=config_yaml_files,
        config_text_cache=config_text_cache,
    )
    composite_ids = _iter_composite_pipeline_ids(
        composite_dir=composite_dir,
        config_text_cache=config_text_cache,
    )
    expected_ids = sorted(provider_ids + composite_ids)

    reference_text = Path("docs/04-reference/pipelines/README.md").read_text(
        encoding="utf-8"
    )
    documented_ids = _extract_documented_pipeline_ids(reference_text)

    missing_in_docs = sorted(set(expected_ids) - set(documented_ids))
    extra_in_docs = sorted(set(documented_ids) - set(expected_ids))

    assert not missing_in_docs and not extra_in_docs, (
        "Pipeline IDs mismatch between configs and "
        "docs/04-reference/pipelines/README.md\n"
        f"Missing in docs: {missing_in_docs}\n"
        f"Unexpected in docs: {extra_in_docs}"
    )


def test_adr_numbers_are_unique() -> None:
    """ADR filenames MUST have unique numbers (no ADR-XXX duplicates)."""
    decisions_dir = Path("docs/02-architecture/decisions")
    adr_files = sorted(decisions_dir.glob("ADR-*.md"))
    numbers = [
        match.group(1)
        for path in adr_files
        if (match := re.match(r"ADR-(\d{3})-[a-z0-9-]+\.md$", path.name))
    ]
    duplicates = [num for num, count in Counter(numbers).items() if count > 1]
    assert not duplicates, f"Duplicate ADR numbers found: {sorted(duplicates)}"


def test_adr_index_links_match_decision_files() -> None:
    """ADR index in README MUST match decision files on disk."""
    decisions_dir = Path("docs/02-architecture/decisions")
    readme_path = decisions_dir / "README.md"

    adr_files = {path.name for path in decisions_dir.glob("ADR-*.md")}
    readme_text = readme_path.read_text(encoding="utf-8")
    linked_files = set(
        re.findall(
            r"\(ADR-\d{3}-[a-z0-9-]+\.md\)",
            readme_text,
        )
    )
    linked_files = {item.strip("()") for item in linked_files}

    missing_from_index = sorted(adr_files - linked_files)
    missing_on_disk = sorted(linked_files - adr_files)

    assert not missing_from_index and not missing_on_disk, (
        "ADR index mismatch.\n"
        f"Missing in README index: {missing_from_index}\n"
        f"Missing on disk: {missing_on_disk}"
    )


def test_adr_h1_number_matches_filename() -> None:
    """ADR H1 heading number should match filename number."""
    decisions_dir = Path("docs/02-architecture/decisions")
    mismatches: list[str] = []

    for path in sorted(decisions_dir.glob("ADR-*.md")):
        file_match = re.match(r"ADR-(\d{3})-", path.name)
        if file_match is None:
            continue
        file_number = file_match.group(1)
        text = path.read_text(encoding="utf-8")
        h1_match = re.search(r"^#\s+ADR-(\d{3})\b", text, flags=re.MULTILINE)
        if h1_match is None:
            continue
        title_number = h1_match.group(1)
        if title_number != file_number:
            mismatches.append(f"{path.name}: heading ADR-{title_number}")

    assert not mismatches, "ADR heading/filename mismatch:\n" + "\n".join(mismatches)


def test_adr_status_is_from_allowed_set() -> None:
    """Each ADR file must declare a status from the allowed normalized set."""
    decisions_dir = Path("docs/02-architecture/decisions")
    allowed_statuses = {"accepted", "superseded", "deprecated", "added"}
    violations = _iter_adr_status_violations(
        decisions_dir=decisions_dir,
        allowed_statuses=allowed_statuses,
    )
    assert not violations, "ADR status validation failed:\n" + "\n".join(violations)


def test_mkdocs_nav_references_existing_markdown_files() -> None:
    """All markdown paths referenced in mkdocs navigation MUST exist."""
    raw = Path("mkdocs.yml").read_text(encoding="utf-8")
    # Only scan lines after `nav:` — exclude_docs and other top-level keys
    # may contain glob patterns that look like .md paths but aren't nav entries.
    nav_start = raw.find("\nnav:")
    if nav_start == -1:
        return
    nav_section = raw[nav_start:]
    active_lines = [
        line for line in nav_section.splitlines() if not line.lstrip().startswith("#")
    ]
    nav_paths = sorted(
        set(re.findall(r"\b([A-Za-z0-9_./-]+\.md)\b", "\n".join(active_lines)))
    )

    missing = [path for path in nav_paths if not (Path("docs") / path).exists()]
    assert not missing, (
        "mkdocs.yml contains links to missing markdown files:\n"
        + "\n".join(f"  - {item}" for item in missing)
    )


def test_no_legacy_repo_slug_in_active_docs_and_workflows(
    docs_markdown_files: list[Path],
    docs_text_cache: dict[Path, str],
    workflow_text_cache: dict[Path, str],
) -> None:
    """Active docs/workflows should reference the current repository slug."""
    legacy_slug = re.compile(r"SatoryKono/BioactivityDataAcquisition2")
    candidates = [Path("README.md")]
    candidates.extend(_iter_active_docs_markdown(docs_markdown_files))
    candidates.extend(workflow_text_cache)

    violations: list[str] = []
    for path in candidates:
        if path == Path("README.md"):
            text = path.read_text(encoding="utf-8")
        elif path in workflow_text_cache:
            text = workflow_text_cache[path]
        else:
            text = docs_text_cache[path]
        if legacy_slug.search(text):
            violations.append(path.as_posix())

    assert not violations, (
        "Legacy repository slug found (expected BioactivityDataAcquisition):\n"
        + "\n".join(f"  - {item}" for item in sorted(violations))
    )


def test_no_legacy_contract_path_in_active_docs(
    docs_markdown_files: list[Path],
    docs_text_cache: dict[Path, str],
) -> None:
    """Active docs should use docs/04-reference/contracts/gold path."""
    legacy_path = "docs/contracts/gold/"
    candidates = [Path("README.md")]
    candidates.extend(_iter_active_docs_markdown(docs_markdown_files))

    violations: list[str] = []
    for path in candidates:
        text = (
            path.read_text(encoding="utf-8")
            if path == Path("README.md")
            else docs_text_cache[path]
        )
        if legacy_path in text:
            violations.append(path.as_posix())

    assert not violations, (
        "Legacy contracts path found (expected docs/04-reference/contracts/gold):\n"
        + "\n".join(f"  - {item}" for item in sorted(violations))
    )


def test_root_readme_uses_current_docs_entrypoints() -> None:
    """README must keep the current active-doc entrypoints and avoid stale trees."""
    text = Path("README.md").read_text(encoding="utf-8")

    required_tokens = (
        "docs/04-reference/cli.md",
        "docs/04-reference/contracts/run-manifest-ledger.md",
        "docs/00-project/00-map.md",
        "docs/99-archive/README.md",
    )
    legacy_tokens = (
        "docs/cli/INDEX.md",
        "docs/02-pipelines/",
        "docs/operations/",
    )

    for token in required_tokens:
        assert token in text, f"README.md is missing current docs entrypoint: {token}"
    for token in legacy_tokens:
        assert token not in text, (
            f"README.md reintroduced a stale docs entrypoint: {token}"
        )


def test_no_legacy_kebab_pipeline_ids_in_active_docs(
    docs_markdown_files: list[Path],
    docs_text_cache: dict[Path, str],
    workflow_text_cache: dict[Path, str],
) -> None:
    """Active docs/workflows should use underscore pipeline IDs."""
    legacy_pipeline_ids = {
        "chembl-protein-class",
        "chembl-cell-line",
        "chembl-molecule",
        "chembl-target",
        "chembl-activity",
        "chembl-assay",
        "chembl-publication",
        "chembl-assay-parameters",
        "chembl-compound-record",
        "chembl-target-component",
        "chembl-publication-term",
        "chembl-publication-similarity",
        "chembl-subcellular-fraction",
        "chembl-tissue",
        "uniprot-protein",
        "uniprot-idmapping",
        "pubchem-compound",
        "pubmed-publication",
        "crossref-publication",
        "openalex-publication",
        "semanticscholar-publication",
        "composite-publication",
        "composite-molecule",
        "composite-target",
        "composite-activity",
        "composite-assay",
    }

    candidates = [Path("README.md")]
    candidates.extend(_iter_active_docs_markdown(docs_markdown_files))
    candidates.extend(workflow_text_cache)

    violations: list[str] = []
    # Match legacy kebab pipeline IDs as tokens, not as substrings of
    # artifact names like reports/e2e/chembl-activity-smoke.xml.
    legacy_patterns = [
        re.compile(rf"(?<![A-Za-z0-9_]){re.escape(item)}(?![A-Za-z0-9_])")
        for item in legacy_pipeline_ids
    ]
    for path in candidates:
        if path == Path("README.md"):
            text = path.read_text(encoding="utf-8")
        elif path in workflow_text_cache:
            text = workflow_text_cache[path]
        else:
            text = docs_text_cache[path]
        if any(pattern.search(text) for pattern in legacy_patterns):
            violations.append(path.as_posix())

    assert not violations, (
        "Legacy kebab-case pipeline IDs found in active docs/workflows:\n"
        + "\n".join(f"  - {item}" for item in sorted(violations))
    )


def test_generated_docs_artifacts_excluded_from_active_scope(
    docs_markdown_files: list[Path],
) -> None:
    """Generated docs must be audited by dedicated gates, not active docs sync scope."""
    active_paths = {
        path.as_posix() for path in _iter_active_docs_markdown(docs_markdown_files)
    }
    generated_paths = [
        path.as_posix() for path in _iter_generated_docs_markdown(docs_markdown_files)
    ]
    overlap = sorted(set(generated_paths) & active_paths)
    assert not overlap, (
        "Generated docs leaked into active docs sync scope:\n"
        + "\n".join(f"  - {item}" for item in overlap)
    )


def test_report_docs_excluded_from_active_scope(
    docs_markdown_files: list[Path],
) -> None:
    """Dated/internal reports must not participate in canonical active-doc sync checks."""
    active_paths = {
        path.as_posix() for path in _iter_active_docs_markdown(docs_markdown_files)
    }
    report_paths = {
        path.as_posix() for path in _iter_report_docs_markdown(docs_markdown_files)
    }
    overlap = sorted(active_paths & report_paths)
    assert not overlap, "Report docs leaked into active docs sync scope:\n" + "\n".join(
        f"  - {item}" for item in overlap
    )


def test_generated_zone_docs_excluded_from_active_scope(
    docs_markdown_files: list[Path],
) -> None:
    """Generated documentation zones must not be treated as canonical active docs."""
    active_paths = {
        path.as_posix() for path in _iter_active_docs_markdown(docs_markdown_files)
    }
    generated_zone_paths = {
        path.as_posix() for path in _iter_generated_zone_markdown(docs_markdown_files)
    }
    overlap = sorted(active_paths & generated_zone_paths)
    assert not overlap, (
        "Generated-zone docs leaked into active docs sync scope:\n"
        + "\n".join(f"  - {item}" for item in overlap)
    )


def test_canonical_doc_roots_are_active_scope_only(
    docs_markdown_files: list[Path],
) -> None:
    """Canonical documentation roots should not resolve to reports/exports/generated zones."""
    canonical_paths = {
        path.as_posix() for path in _iter_canonical_docs_markdown(docs_markdown_files)
    }
    noncanonical_suffixes = (
        "docs/reports/",
        "docs/exports/",
        "docs/02-architecture/generated/",
    )
    leaked = sorted(
        path
        for path in canonical_paths
        if any(fragment in path for fragment in noncanonical_suffixes)
    )
    assert not leaked, (
        "Canonical docs iterator leaked non-canonical paths:\n"
        + "\n".join(f"  - {item}" for item in leaked)
    )


def test_generated_export_markdown_has_generation_marker(
    docs_markdown_files: list[Path],
    docs_text_cache: dict[Path, str],
) -> None:
    """Generated merged docs in docs/exports must contain explicit generation marker."""
    merged_docs = sorted(
        path
        for path in docs_markdown_files
        if path.parent == DOCS_ROOT / "exports" and path.name.endswith(".merged.md")
    )
    for path in merged_docs:
        lines = docs_text_cache[path].splitlines()
        head = "\n".join(lines[:30])
        assert re.search(r"^_Generated:\s+\d{4}-\d{2}-\d{2}_$", head, re.MULTILINE), (
            f"Missing generation marker in {path.as_posix()}"
        )


def test_generated_export_report_names_are_timestamped(
    docs_markdown_files: list[Path],
) -> None:
    """Generated docs export reports must follow timestamped naming convention."""
    bad_names = sorted(
        path.as_posix()
        for path in docs_markdown_files
        if path.parent == DOCS_ROOT / "reports"
        and path.name.startswith("docs-export-report-")
        and GENERATED_DOCS_EXPORT_REPORT_RE.match(
            path.relative_to(DOCS_ROOT).as_posix()
        )
        is None
    )
    assert not bad_names, (
        "Generated docs export reports with invalid naming:\n"
        + "\n".join(f"  - {item}" for item in bad_names)
    )


def test_quarantine_states_match_docs() -> None:
    code = Path("src/bioetl/domain/aggregates/_quarantine_value_objects.py").read_text(
        encoding="utf-8"
    )
    states = re.findall(r'^\s+([A-Z_]+)\s*=\s*"[a-z_]+"', code, flags=re.M)
    doc = Path("docs/02-architecture/01-domain-layer.md").read_text(encoding="utf-8")
    missing = [s for s in states if s not in doc]
    assert not missing, f"Missing states in docs: {missing}"


def test_exit_codes_match_docs() -> None:
    """Check that project-specific exit codes are documented.

    BSD sysexits (EX_DATAERR..EX_NOPERM) are standard boilerplate
    and not required in project docs.
    """
    bsd_sysexits = {
        "EX_DATAERR",
        "EX_NOINPUT",
        "EX_NOUSER",
        "EX_NOHOST",
        "EX_UNAVAILABLE",
        "EX_SOFTWARE",
        "EX_OSERR",
        "EX_OSFILE",
        "EX_CANTCREAT",
        "EX_IOERR",
        "EX_TEMPFAIL",
        "EX_PROTOCOL",
        "EX_NOPERM",
    }
    code = Path("src/bioetl/interfaces/cli/exit_codes.py").read_text(encoding="utf-8")
    names = re.findall(r"^\s+([A-Z_]+)\s*=\s*\d+", code, flags=re.M)
    doc = Path("docs/04-reference/cli.md").read_text(encoding="utf-8")
    missing = [n for n in names if n not in doc and n not in bsd_sysexits]
    assert not missing, (
        f"Exit codes missing in docs/04-reference/cli.md: {missing[:10]}"
    )
