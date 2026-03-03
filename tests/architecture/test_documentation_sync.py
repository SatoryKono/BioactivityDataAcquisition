from __future__ import annotations

from collections import Counter
import re
from pathlib import Path

import yaml


def _resolve_composite_config_dir() -> Path:
    return Path("configs/composites")


def test_ports_count_matches_docs() -> None:
    actual = len(list(Path("src/bioetl/domain/ports").glob("*.py")))
    text = Path("docs/02-architecture/01-domain-layer.md").read_text(encoding="utf-8")
    assert str(actual) in text, (
        f"Ports count {actual} not reflected in docs/02-architecture/01-domain-layer.md"
    )


def test_pipeline_count_matches_docs() -> None:
    entities_dir = Path("configs/entities")
    composite_dir = _resolve_composite_config_dir()
    standard = [
        p
        for p in entities_dir.rglob("*.yaml")
        if p.name not in {"_base.yaml", "_schema.json"}
    ]
    composite = list(composite_dir.glob("*.yaml"))
    text = Path("docs/04-reference/pipelines/README.md").read_text(encoding="utf-8")
    assert str(len(standard)) in text and str(len(composite)) in text


def test_pipeline_ids_match_reference_index() -> None:
    """Pipeline IDs in reference index must match config-defined IDs."""
    entities_dir = Path("configs/entities")
    composite_dir = _resolve_composite_config_dir()
    provider_ids: list[str] = []
    for path in sorted(entities_dir.rglob("*.yaml")):
        if path.name in {"_base.yaml", "_schema.json"}:
            continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            continue
        pipeline = raw.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        pipeline_name = pipeline.get("pipeline_name")
        if isinstance(pipeline_name, str):
            provider_ids.append(pipeline_name)

    composite_ids: list[str] = []
    for path in sorted(composite_dir.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        match = re.search(
            r"^\s*name:\s*(composite_[a-z0-9_]+)\s*$", text, flags=re.MULTILINE
        )
        if match is not None:
            composite_ids.append(match.group(1))

    expected_ids = sorted(provider_ids + composite_ids)

    reference_text = Path("docs/04-reference/pipelines/README.md").read_text(
        encoding="utf-8"
    )
    documented_ids = sorted(
        set(
            re.findall(
                r"\|\s*\d+\s*\|\s*`([a-z0-9_]+)`\s*\|",
                reference_text,
                flags=re.MULTILINE,
            )
        )
    )

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
    violations: list[str] = []

    status_patterns = (
        re.compile(r"^\*\*Status:\*\*\s*(.+)$", flags=re.MULTILINE),
        re.compile(r"^\*\s+\*\*Status\*\*:\s*(.+)$", flags=re.MULTILINE),
        re.compile(
            r"^\|\s*\*\*Статус\*\*\s*\|\s*(.+?)\s*\|$",
            flags=re.MULTILINE,
        ),
        re.compile(
            r"^\|\s*\*\*Status\*\*\s*\|\s*(.+?)\s*\|$",
            flags=re.MULTILINE,
        ),
    )

    for path in sorted(decisions_dir.glob("ADR-*.md")):
        text = path.read_text(encoding="utf-8")
        raw_status: str | None = None
        for pattern in status_patterns:
            match = pattern.search(text)
            if match is not None:
                raw_status = match.group(1).strip()
                break

        if raw_status is None:
            violations.append(f"{path.name}: missing status field")
            continue

        normalized = re.split(r"[\s(]", raw_status, maxsplit=1)[0].strip().lower()
        if normalized not in allowed_statuses:
            violations.append(
                f"{path.name}: invalid status '{raw_status}' "
                f"(allowed: {sorted(allowed_statuses)})"
            )

    assert not violations, "ADR status validation failed:\n" + "\n".join(violations)


def test_mkdocs_nav_references_existing_markdown_files() -> None:
    """All markdown paths referenced in mkdocs navigation MUST exist."""
    mkdocs_text = Path("mkdocs.yml").read_text(encoding="utf-8")
    nav_paths = sorted(set(re.findall(r"\b([A-Za-z0-9_./-]+\.md)\b", mkdocs_text)))

    missing = [path for path in nav_paths if not (Path("docs") / path).exists()]
    assert not missing, (
        "mkdocs.yml contains links to missing markdown files:\n"
        + "\n".join(f"  - {item}" for item in missing)
    )


def test_no_legacy_repo_slug_in_active_docs_and_workflows() -> None:
    """Active docs/workflows should reference the current repository slug."""
    legacy_slug = re.compile(r"SatoryKono/BioactivityDataAcquisition(?!2)")
    excluded_doc_parts = {"99-archive", "exports"}

    candidates = [Path("README.md")]
    candidates.extend(
        path
        for path in Path("docs").rglob("*.md")
        if excluded_doc_parts.isdisjoint(path.parts)
    )
    candidates.extend(Path(".github/workflows").glob("*.yml"))

    violations: list[str] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if legacy_slug.search(text):
            violations.append(path.as_posix())

    assert not violations, (
        "Legacy repository slug found (expected BioactivityDataAcquisition2):\n"
        + "\n".join(f"  - {item}" for item in sorted(violations))
    )


def test_no_legacy_contract_path_in_active_docs() -> None:
    """Active docs should use docs/04-reference/contracts/gold path."""
    legacy_path = "docs/contracts/gold/"
    candidates = [Path("README.md")]
    candidates.extend(
        path for path in Path("docs").rglob("*.md") if "99-archive" not in path.parts
    )

    violations: list[str] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if legacy_path in text:
            violations.append(path.as_posix())

    assert not violations, (
        "Legacy contracts path found (expected docs/04-reference/contracts/gold):\n"
        + "\n".join(f"  - {item}" for item in sorted(violations))
    )


def test_no_legacy_kebab_pipeline_ids_in_active_docs() -> None:
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
    candidates.extend(
        path for path in Path("docs").rglob("*.md") if "99-archive" not in path.parts
    )
    candidates.extend(Path(".github/workflows").glob("*.yml"))

    violations: list[str] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if any(item in text for item in legacy_pipeline_ids):
            violations.append(path.as_posix())

    assert not violations, (
        "Legacy kebab-case pipeline IDs found in active docs/workflows:\n"
        + "\n".join(f"  - {item}" for item in sorted(violations))
    )


def test_quarantine_states_match_docs() -> None:
    code = Path("src/bioetl/domain/aggregates/quarantine_entry.py").read_text(
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
