#!/usr/bin/env python3
"""Run config-surface burn-down phases using surgical text edits (preserve formatting)."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCORECARD = ROOT / "configs/quality/debt_scorecard.yaml"
BASELINE = ROOT / "reports/quality/config-discrepancy-baseline.json"

COMPOSITE_ENRICHER_STUB = """
      {name}:
        soft_fail_threshold: 1.0
        hard_fail_threshold: 1.0"""

COMPOSITE_ENRICHER_STUB_DEEP = """
            {name}:
                soft_fail_threshold: 1.0
                hard_fail_threshold: 1.0"""


@dataclass(frozen=True)
class PhaseResult:
    phase: int
    name: str
    entity_inconsistent: int
    composite_inconsistent: int
    files_touched: int


def _entity_paths() -> list[Path]:
    return sorted(
        p
        for p in (ROOT / "configs/entities").glob("*/*.yaml")
        if not p.name.startswith("_") and p.parent.name != "composite"
    )


def _composite_paths() -> list[Path]:
    return sorted(
        p
        for p in (ROOT / "configs/composites").glob("*.yaml")
        if not p.name.startswith("_")
    )


def _read(path: Path) -> str:
    from scripts.engineering.common.repo_paths import ensure_repo_path

    return ensure_repo_path(path).read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, ensure_repo_path

    safe_root = REPO_ROOT.resolve(strict=False)
    confined_path = ensure_repo_path(path)
    relative_path = confined_path.relative_to(safe_root)
    safe_path = safe_root.joinpath(*relative_path.parts)
    safe_path.write_text(text, encoding="utf-8")


def _replace(path: Path, old: str, new: str) -> bool:
    text = _read(path)
    if old not in text:
        return False
    _write(path, text.replace(old, new, 1))
    return True


def _metrics() -> tuple[int, int]:
    import yaml

    payload = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    families = payload["families"]
    return (
        int(families["entity_effective"]["inconsistent_parameter_count"]),
        int(families["composite_runtime"]["inconsistent_parameter_count"]),
    )


def _regenerate() -> None:
    subprocess.check_call(
        [sys.executable, "-m", "scripts.schema", "generate-config-matrix", "--update"],
        cwd=ROOT,
    )


def _update_scorecard(entity: int, composite: int) -> None:
    text = SCORECARD.read_text(encoding="utf-8")
    text = re.sub(
        r"(entity_effective:\s*\n(?:.*?\n)*?\s+inconsistent_parameter_count:\s*\n\s+current_count:\s*)\d+(\s*\n\s+max_count:\s*)\d+",
        rf"\g<1>{entity}\g<2>{entity}",
        text,
        count=1,
    )
    text = re.sub(
        r"(composite_runtime:\s*\n(?:.*?\n)*?\s+inconsistent_parameter_count:\s*\n\s+current_count:\s*)\d+(\s*\n\s+max_count:\s*)\d+",
        rf"\g<1>{composite}\g<2>{composite}",
        text,
        count=1,
    )
    SCORECARD.write_text(text, encoding="utf-8")


def _apply_per_file(paths: list[Path], fn: Callable[[Path, str], str | None]) -> int:
    touched = 0
    for path in paths:
        original = _read(path)
        updated = fn(path, original)
        if updated is not None and updated != original:
            _write(path, updated)
            touched += 1
    return touched


def _insert_publication_year_in_ranges_block(block: str) -> str:
    if "publication_year" in block:
        return block
    if "ranges: {}" in block:
        return block.replace(
            "ranges: {}",
            "ranges:\n      publication_year:\n        min: 1950\n        max: 2050",
            1,
        )
    if "ranges:\n        {}" in block:
        return block.replace(
            "ranges:\n        {}",
            "ranges:\n            publication_year:\n                min: 1950\n                max: 2050",
            1,
        )
    return block


def phase_01_gold_publication_year() -> int:
    pub_year = "      publication_year:\n        min: 1950\n        max: 2050\n"
    pub_year_indent8 = "            publication_year:\n                min: 1950\n                max: 2050\n"

    def fn(_path: Path, text: str) -> str | None:
        if "filters.gold_filters" not in text and "gold_filters:" not in text:
            return None
        if re.search(r"gold_filters:[\s\S]*?publication_year:", text):
            return None
        if "  gold_filters:\n    ranges: {}" in text:
            return text.replace(
                "  gold_filters:\n    ranges: {}",
                "  gold_filters:\n    ranges:\n" + pub_year.rstrip("\n"),
                1,
            )
        if "    gold_filters:\n        ranges: {}" in text:
            return text.replace(
                "    gold_filters:\n        ranges: {}",
                "    gold_filters:\n        ranges:\n" + pub_year_indent8.rstrip("\n"),
                1,
            )
        return None

    return _apply_per_file(_entity_paths(), fn)


def phase_02_pipeline_batch_size() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if re.search(r"^  batch_size:", text, re.M) or re.search(
            r"^    batch_size:", text, re.M
        ):
            return None
        # 2-space pipeline block
        if "\n  business_primary_keys:\n" in text and "\npipeline:\n" in text:
            return text.replace(
                "\n  business_primary_keys:\n",
                "\n  batch_size: 1000\n  business_primary_keys:\n",
                1,
            )
        # 4-space nested pipeline block
        match = re.search(
            r"(\n    business_primary_keys:\n(?:        - .+\n)+)",
            text,
        )
        if match:
            block = match.group(1)
            return text.replace(block, block + "    batch_size: 1000\n", 1)
        return None

    return _apply_per_file(_entity_paths(), fn)


def phase_03_schema_field_aliases() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if "field_aliases:" in text.split("schema:", 1)[-1][:2000]:
            return None
        if "schema:" not in text:
            return None
        return text.replace(
            "schema:\n  content_hash:",
            "schema:\n  field_aliases: {}\n  content_hash:",
            1,
        ).replace(
            "schema:\n    content_hash:",
            "schema:\n    field_aliases: {}\n    content_hash:",
            1,
        )

    return _apply_per_file(_entity_paths(), fn)


def phase_04_gold_list_lengths() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if "list_lengths:" in text:
            return None
        if "  gold_filters:\n    ranges:" in text:
            return text.replace(
                "  gold_filters:\n    ranges:",
                "  gold_filters:\n    list_lengths: {}\n    ranges:",
                1,
            )
        if "    gold_filters:\n        ranges:" in text:
            return text.replace(
                "    gold_filters:\n        ranges:",
                "    gold_filters:\n        list_lengths: {}\n        ranges:",
                1,
            )
        return None

    return _apply_per_file(_entity_paths(), fn)


def phase_05_gold_list_contains() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if "list_contains:" in text:
            return None
        if "  gold_filters:\n    list_lengths:" in text:
            return text.replace(
                "  gold_filters:\n    list_lengths:",
                "  gold_filters:\n    list_contains: {}\n    list_lengths:",
                1,
            )
        if "    gold_filters:\n        list_lengths:" in text:
            return text.replace(
                "    gold_filters:\n        list_lengths:",
                "    gold_filters:\n        list_contains: {}\n        list_lengths:",
                1,
            )
        return None

    return _apply_per_file(_entity_paths(), fn)


def phase_06_gold_exclude_if_present() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if re.search(r"gold_filters:[\s\S]{0,800}?exclude_if_present:", text):
            return None
        if "    columns: {}\ncontracts:" in text:
            return text.replace(
                "    columns: {}\ncontracts:",
                "    columns: {}\n    exclude_if_present: []\ncontracts:",
                1,
            )
        if "        required_fields:" in text and "    gold_filters:" in text:
            # append before contracts when gold ends with required_fields block
            return re.sub(
                r"(    gold_filters:[\s\S]*?)(contracts:)",
                r"\1    exclude_if_present: []\n\2",
                text,
                count=1,
            )
        return None

    return _apply_per_file(_entity_paths(), fn)


def phase_07_checkpoint_interval() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if "checkpoint_interval:" in text:
            return None
        if "\n  batch_size: 1000" in text:
            return text.replace(
                "\n  batch_size: 1000",
                "\n  batch_size: 1000\n  checkpoint_interval: 1000",
                1,
            )
        if "\n    batch_size: 1000" in text:
            return text.replace(
                "\n    batch_size: 1000",
                "\n    batch_size: 1000\n    checkpoint_interval: 1000",
                1,
            )
        return None

    return _apply_per_file(_entity_paths(), fn)


def phase_08_input_fallback_column() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if "fallback_column:" in text:
            return None
        if "    batch_size:" in text and "  input_filter:" in text:
            return re.sub(
                r"(    batch_size: \d+\n)(  silver_filters:)",
                r"\1    fallback_column: title\n\2",
                text,
                count=1,
            )
        if "        batch_size:" in text and "    input_filter:" in text:
            return re.sub(
                r"(        batch_size: \d+\n)(    silver_filters:)",
                r"\1        fallback_column: title\n\2",
                text,
                count=1,
            )
        return None

    return _apply_per_file(_entity_paths(), fn)


def phase_09_silver_publication_year() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if re.search(
            r"silver_filters:[\s\S]{0,600}?ranges:[\s\S]{0,200}?publication_year", text
        ):
            return None
        if "  silver_filters:\n    ranges: {}" in text:
            return text.replace(
                "  silver_filters:\n    ranges: {}",
                "  silver_filters:\n    ranges:\n      publication_year:\n        min: 1950\n        max: 2050",
                1,
            )
        if "    columns: {}\n    exclude_if_present:" in text:
            return text.replace(
                "    columns: {}\n    exclude_if_present:",
                "    columns: {}\n    ranges:\n      publication_year:\n        min: 1950\n        max: 2050\n    exclude_if_present:",
                1,
            )
        return None

    return _apply_per_file(_entity_paths(), fn)


def phase_10_hash_exclude() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if "hash_exclude:" in text:
            return None
        return text.replace(
            "  hash_include: []",
            "  hash_include: []\n  hash_exclude: []",
            1,
        ).replace(
            "    hash_include: []",
            "    hash_include: []\n    hash_exclude: []",
            1,
        )

    return _apply_per_file(_entity_paths(), fn)


def phase_11_field_policy() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if "field_policy:" in text:
            return None
        # Prefer 4-space nested pipeline keys before 2-space top-level keys.
        if "    business_primary_keys:" in text:
            return text.replace(
                "    business_primary_keys:",
                "    field_policy: {}\n    business_primary_keys:",
                1,
            )
        if "  business_primary_keys:" in text:
            return text.replace(
                "  business_primary_keys:",
                "  field_policy: {}\n  business_primary_keys:",
                1,
            )
        return None

    return _apply_per_file(_entity_paths(), fn)


def phase_12_quality_metadata() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if re.search(r"^quality:[\s\S]{0,400}?metadata:", text, re.M):
            return None
        if "quality:\n    version:" in text:
            return text.replace(
                "quality:\n    version:",
                "quality:\n    metadata: {}\n    version:",
                1,
            )
        if "quality:\n  version:" in text:
            return text.replace(
                "quality:\n  version:",
                "quality:\n  metadata: {}\n  version:",
                1,
            )
        return None

    return _apply_per_file(_entity_paths(), fn)


def _composite_enricher_phase(names: tuple[str, ...]) -> int:
    markers = (
        ("        enricher_overrides:", COMPOSITE_ENRICHER_STUB_DEEP),
        ("    enricher_overrides:", COMPOSITE_ENRICHER_STUB),
    )

    def fn(_path: Path, text: str) -> str | None:
        updated = text
        changed = False
        for name in names:
            if re.search(rf"^\s+{re.escape(name)}:", updated, re.M):
                continue
            marker, stub_template = next(
                ((m, s) for m, s in markers if m in updated),
                (None, None),
            )
            if marker is None:
                continue
            insert = "".join(stub_template.format(name=name)) + "\n"
            updated = updated.replace(marker, marker + insert, 1)
            changed = True
        return updated if changed else None

    return _apply_per_file(_composite_paths(), fn)


def phase_13_dq_a() -> int:
    return _composite_enricher_phase(
        ("chembl_cell_line", "chembl_compound_record", "chembl_tissue")
    )


def phase_14_dq_b() -> int:
    return _composite_enricher_phase(("pubchem_compound", "pubmed_publication"))


def phase_15_dq_c() -> int:
    return _composite_enricher_phase(
        ("semanticscholar_publication", "uniprot_idmapping", "uniprot_protein")
    )


def phase_16_composite_field_aliases() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if re.search(r"^  field_aliases:", text, re.M) or re.search(
            r"^    field_aliases:", text, re.M
        ):
            return None
        return text.replace(
            "  normalized_join_key_policy:",
            "  field_aliases: {}\n  normalized_join_key_policy:",
            1,
        ).replace(
            "    normalized_join_key_policy:",
            "    field_aliases: {}\n    normalized_join_key_policy:",
            1,
        )

    return _apply_per_file(_composite_paths(), fn)


def phase_17_lineage_chembl() -> int:
    chembl_block_shallow = (
        "    provider_lookup_fields:\n"
        "      chembl:\n"
        "        _lookup_method: chembl_lookup_method\n"
        "        _original_id: chembl_original_id"
    )
    chembl_block_deep = (
        "        provider_lookup_fields:\n"
        "            chembl:\n"
        "                _lookup_method: chembl_lookup_method\n"
        "                _original_id: chembl_original_id"
    )

    def fn(_path: Path, text: str) -> str | None:
        if re.search(r"provider_lookup_fields:[\s\S]{0,400}?chembl:", text):
            return None
        if "        provider_lookup_fields:" in text:
            return text.replace(
                "        provider_lookup_fields:",
                chembl_block_deep,
                1,
            )
        if "    provider_lookup_fields:" in text:
            return text.replace(
                "    provider_lookup_fields:",
                chembl_block_shallow,
                1,
            )
        return None

    return _apply_per_file(_composite_paths(), fn)


def phase_18_schema_content_hash() -> int:
    # noop if already universal
    return 0


def phase_19_filters_identity() -> int:
    return 0


def phase_20_composite_cross_validation_disabled() -> int:
    def fn(_path: Path, text: str) -> str | None:
        if "cross_validation:" in text:
            return None
        marker = "  dq_overrides:"
        if marker not in text:
            return None
        block = (
            "  cross_validation:\n"
            "    enabled: false\n"
            "    warning_threshold: 1\n"
            "    error_threshold: 2\n"
            "    quarantine_threshold: 2\n"
            "    fuzzy_threshold: 0.8\n"
            "    numeric_tolerance: 0.10\n"
            "    enricher_pairings: []\n\n"
        )
        return text.replace(marker, block + marker, 1)

    return _apply_per_file(_composite_paths(), fn)


PHASES: list[tuple[str, Callable[[], int]]] = [
    ("gold publication_year", phase_01_gold_publication_year),
    ("pipeline batch_size", phase_02_pipeline_batch_size),
    ("schema field_aliases", phase_03_schema_field_aliases),
    ("gold list_lengths", phase_04_gold_list_lengths),
    ("gold list_contains", phase_05_gold_list_contains),
    ("gold exclude_if_present", phase_06_gold_exclude_if_present),
    ("checkpoint_interval", phase_07_checkpoint_interval),
    ("input fallback_column", phase_08_input_fallback_column),
    ("silver publication_year", phase_09_silver_publication_year),
    ("contracts hash_exclude", phase_10_hash_exclude),
    ("pipeline field_policy", phase_11_field_policy),
    ("quality metadata", phase_12_quality_metadata),
    ("composite dq batch A", phase_13_dq_a),
    ("composite dq batch B", phase_14_dq_b),
    ("composite dq batch C", phase_15_dq_c),
    ("composite field_aliases", phase_16_composite_field_aliases),
    ("composite lineage chembl", phase_17_lineage_chembl),
    ("schema content_hash noop", phase_18_schema_content_hash),
    ("filters identity noop", phase_19_filters_identity),
    (
        "composite cross_validation disabled",
        phase_20_composite_cross_validation_disabled,
    ),
]


def run(count: int = 20, start: int = 1) -> list[PhaseResult]:
    results: list[PhaseResult] = []
    for idx, (name, handler) in enumerate(PHASES[:count], start=1):
        if idx < start:
            continue
        touched = handler()
        _regenerate()
        entity, composite = _metrics()
        results.append(PhaseResult(idx, name, entity, composite, touched))
        print(
            f"Phase {idx:02d} {name}: touched={touched} entity={entity} composite={composite}"
        )
    entity, composite = _metrics()
    _update_scorecard(entity, composite)
    print(f"FINAL entity={entity} composite={composite}")
    return results


if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run(20, start=start)
