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
"""CI invariants for configs/** directory.

Ensures structural integrity of all YAML configuration files:
  INV-CFG-001: No legacy naming (document→publication, dq/→quality/, filter/→filters/)
  INV-CFG-002: Unified entity sections (schema/quality/filters/contracts) and provider config exist
  INV-CFG-003: loading_strategy is null or a valid LoadingStrategy enum value
  INV-CFG-004: Providers with config-bound auth declare named environment references
  INV-CFG-005: No unknown keys in unified entity/composite/provider configs
  INV-CFG-006: pipeline_name matches {provider}_{entity_type} convention

Reference:
    ADR-024 (entity naming), ADR-027 (DQ externalization), ADR-028 (filter
    externalization), ADR-029 (convention-based path resolution), ADR-031
    (loading strategy), ADR-039 (unified entity configuration format).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import re
import pytest
import yaml

from bioetl.domain.constants import META_FIELDS
from bioetl.domain.models.filter import compute_extraction_params_sha256
from bioetl.infrastructure.config.config_ci_contract import (
    COMPOSITE_ALLOWED_KEYS,
    CONTRACT_ALLOWED_KEYS,
    ENTITY_ALLOWED_KEYS,
    FILTER_ALLOWED_KEYS,
    LEGACY_ENTITY_NAMES,
    LEGACY_PATH_FRAGMENTS,
    PIPELINE_ALLOWED_KEYS,
    PROVIDER_ALLOWED_KEYS,
    PROVIDER_AUTH_REQUIREMENTS,
    QUALITY_ALLOWED_KEYS,
    REQUIRED_ENTITY_SECTIONS,
    EXTRACTION_PARAM_ALLOWLIST,
    RETIRED_PIPELINE_KEYS,
    TRANSITIONAL_PIPELINE_KEYS,
    VALID_LOADING_STRATEGIES,
)
from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)
from scripts.schema.validation import (
    audit_effective_optionality as optionality_audit_script,
)
from scripts.schema.validation import check_config_invariants as invariant_script
from scripts.schema.validation import (
    check_required_filter_fields as required_filter_script,
)
from scripts.schema.validation.validate_pipeline_configs import _canonical_script

pytestmark = pytest.mark.architecture

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = PROJECT_ROOT / "configs"
ENTITIES_DIR = CONFIGS_DIR / "entities"
COMPOSITES_DIR = CONFIGS_DIR / "composites"
PROVIDERS_DIR = CONFIGS_DIR / "providers"
BRONZE_INPUT_DIR = PROJECT_ROOT / "data" / "input" / "bronze"
BRONZE_FIXTURE_GAPS_PATH = CONFIGS_DIR / "base" / "bronze_fixture_gaps.yaml"
BRONZE_FIXTURE_MANIFEST_PATH = CONFIGS_DIR / "base" / "bronze_fixture_manifest.yaml"

# ---------------------------------------------------------------------------
# Known providers and canonical data
# ---------------------------------------------------------------------------
KNOWN_PROVIDERS: set[str] = {
    "chembl",
    "crossref",
    "openalex",
    "pubchem",
    "pubmed",
    "semanticscholar",
    "uniprot",
    "composite",
}

SCD2_CANDIDATE_CONFIGS: tuple[Path, ...] = tuple(
    PROJECT_ROOT / relative_path
    for relative_path in (
        "configs/entities/chembl/publication.yaml",
        "configs/entities/pubmed/publication.yaml",
        "configs/entities/crossref/publication.yaml",
        "configs/entities/openalex/publication.yaml",
        "configs/entities/semanticscholar/publication.yaml",
        "configs/entities/chembl/assay.yaml",
        "configs/entities/chembl/assay_parameters.yaml",
        "configs/entities/chembl/cell_line.yaml",
        "configs/entities/chembl/tissue.yaml",
        "configs/entities/chembl/protein_class.yaml",
        "configs/entities/chembl/subcellular_fraction.yaml",
        "configs/entities/chembl/target.yaml",
        "configs/entities/chembl/target_component.yaml",
        "configs/entities/chembl/molecule.yaml",
        "configs/entities/chembl/compound_record.yaml",
        "configs/entities/uniprot/protein.yaml",
        "configs/entities/uniprot/idmapping.yaml",
        "configs/entities/pubchem/compound.yaml",
    )
)

REQUIRED_SCD_CONFIG_KEYS: set[str] = {
    "valid_from_col",
    "valid_to_col",
    "current_flag_col",
    "version_col",
}

LEGACY_SCD_CONFIG_KEYS: set[str] = {"valid_from", "valid_to", "is_current", "version"}
SEMANTIC_SILVER_FILTER_KEYS: set[str] = {
    "columns",
    "ranges",
    "list_lengths",
    "list_contains",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@cache
def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict on parse failure."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return {}
    return data


@cache
def _collect_pipeline_configs() -> list[Path]:
    """Collect unified provider/entity pipeline configs from configs/entities.

    Composite runtime uses configs/composites/*.yaml and composite-specific
    bootstrap contracts, so legacy configs/entities/composite/*.yaml are not
    part of the unified entity invariant surface enforced in this module.
    """
    result: list[Path] = []
    for path in ENTITIES_DIR.rglob("*.yaml"):
        if path.name.startswith("_"):
            continue
        data = _load_yaml(path)
        provider = str(data.get("provider", path.parent.name))
        if provider == "composite":
            continue
        result.append(path)
    return sorted(result)


@cache
def _collect_composite_configs() -> list[Path]:
    """Collect all composite YAML configs."""
    return sorted(
        p for p in COMPOSITES_DIR.glob("*.yaml") if not p.name.startswith("_")
    )


@cache
def _collect_provider_configs() -> list[Path]:
    """Collect unified provider YAML configs."""
    return sorted(p for p in PROVIDERS_DIR.glob("*.yaml") if not p.name.startswith("_"))


def _collect_filter_sections() -> list[tuple[Path, str, dict[str, Any]]]:
    """Collect active filter sections that can contain silver_filters."""
    sections: list[tuple[Path, str, dict[str, Any]]] = []

    base_path = CONFIGS_DIR / "base" / "pipeline.yaml"
    base_filters = _load_yaml(base_path).get("filter_defaults")
    if isinstance(base_filters, dict):
        sections.append((base_path, "filter_defaults", base_filters))

    for path in _collect_provider_configs():
        provider_filters = _load_yaml(path).get("filters")
        if isinstance(provider_filters, dict):
            sections.append((path, "filters", provider_filters))

    for path in _collect_pipeline_configs():
        entity_filters = _load_yaml(path).get("filters")
        if isinstance(entity_filters, dict):
            sections.append((path, "filters", entity_filters))

    return sections


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def _deep_string_search(obj: Any, fragment: str) -> bool:
    """Recursively search for *fragment* in all string values of a YAML tree."""
    if isinstance(obj, str):
        return fragment in obj
    if isinstance(obj, dict):
        return any(_deep_string_search(v, fragment) for v in obj.values())
    if isinstance(obj, list):
        return any(_deep_string_search(item, fragment) for item in obj)
    return False


def _collect_input_jsonl_files(provider: str, entity: str) -> list[Path]:
    fixture_dir = BRONZE_INPUT_DIR / provider / entity
    if not fixture_dir.exists() or not fixture_dir.is_dir():
        return []
    return sorted(fixture_dir.rglob("*.jsonl"))


def _count_jsonl_lines(files: list[Path], stop_after: int | None = None) -> int:
    total = 0
    for path in files:
        with path.open("r", encoding="utf-8") as handle:
            for _ in handle:
                total += 1
                if stop_after is not None and total >= stop_after:
                    return total
    return total


@cache
def _load_bronze_fixture_gaps() -> dict[str, dict[str, Any]]:
    data = _load_yaml(BRONZE_FIXTURE_GAPS_PATH)
    raw_gaps = data.get("gaps")
    if not isinstance(raw_gaps, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for key, value in raw_gaps.items():
        if not isinstance(key, str):
            continue
        if not isinstance(value, dict):
            continue
        result[key] = value
    return result


@cache
def _load_bronze_fixture_manifest() -> dict[str, dict[str, Any]]:
    data = _load_yaml(BRONZE_FIXTURE_MANIFEST_PATH)
    raw_fixtures = data.get("fixtures")
    if not isinstance(raw_fixtures, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for key, value in raw_fixtures.items():
        if not isinstance(key, str):
            continue
        if not isinstance(value, dict):
            continue
        result[key] = value
    return result


def _pipeline_fixture_context(
    config_path: Path,
) -> tuple[str, str, str, list[Path], int]:
    data = _load_yaml(config_path)
    provider = str(data.get("provider", config_path.parent.name))
    entity = str(data.get("entity", config_path.stem))
    key = f"{provider}/{entity}"
    runtime_fixture_files = _collect_input_jsonl_files(provider, entity)
    runtime_fixture_lines = _count_jsonl_lines(runtime_fixture_files)
    return key, provider, entity, runtime_fixture_files, runtime_fixture_lines


def _validate_manifest_entry(
    key: str,
    manifest_entry: dict[str, Any] | None,
    *,
    allowed_fixture_kinds: set[str],
    allowed_validation_statuses: set[str],
    min_tracked_sample_records: int,
) -> tuple[list[str], bool]:
    """Validate a manifest entry."""
    if manifest_entry is None:
        return [], False

    invalid_entries: list[str] = []
    has_manifest_fixture = False

    _validate_fixture_kind(key, manifest_entry, allowed_fixture_kinds, invalid_entries)
    has_manifest_fixture = _validate_fixture_path(
        key, manifest_entry, min_tracked_sample_records, invalid_entries
    )
    _validate_required_fields(key, manifest_entry, invalid_entries)
    _validate_validation_status(
        key, manifest_entry, allowed_validation_statuses, invalid_entries
    )

    return invalid_entries, has_manifest_fixture


def _validate_fixture_kind(
    key: str,
    manifest_entry: dict[str, Any],
    allowed_fixture_kinds: set[str],
    invalid_entries: list[str],
) -> None:
    """Validate the fixture kind."""
    fixture_kind = manifest_entry.get("fixture_kind")
    if fixture_kind not in allowed_fixture_kinds:
        invalid_entries.append(
            f"{key}: fixture_kind must be one of {sorted(allowed_fixture_kinds)}"
        )


def _validate_fixture_path(
    key: str,
    manifest_entry: dict[str, Any],
    min_tracked_sample_records: int,
    invalid_entries: list[str],
) -> bool:
    """Validate the fixture path."""
    has_manifest_fixture = False
    fixture_kind = manifest_entry.get("fixture_kind")
    fixture_path_raw = manifest_entry.get("fixture_path")
    if not isinstance(fixture_path_raw, str) or not fixture_path_raw.strip():
        invalid_entries.append(f"{key}: fixture_path is required in manifest")
        return has_manifest_fixture

    fixture_path = PROJECT_ROOT / fixture_path_raw
    if not fixture_path.exists() or not fixture_path.is_file():
        invalid_entries.append(
            f"{key}: fixture_path does not exist: {fixture_path_raw}"
        )
        return has_manifest_fixture

    if fixture_path.suffix != ".jsonl":
        invalid_entries.append(
            f"{key}: fixture_path must point to .jsonl file, found {fixture_path_raw}"
        )
        return has_manifest_fixture

    manifest_lines = _count_jsonl_lines([fixture_path])
    records = manifest_entry.get("records")
    if not isinstance(records, int) or records <= 0:
        invalid_entries.append(f"{key}: records must be positive int in manifest")
        return has_manifest_fixture

    if records != manifest_lines:
        invalid_entries.append(
            f"{key}: records={records} does not match fixture "
            f"line count={manifest_lines}"
        )
        return has_manifest_fixture

    if fixture_kind in {"tracked_ci_sample", "tracked_edge_case_sample"}:
        if not fixture_path_raw.startswith("tests/fixtures/bronze/"):
            invalid_entries.append(
                f"{key}: {fixture_kind} must live under tests/fixtures/bronze/"
            )
        if fixture_kind == "tracked_ci_sample" and records < min_tracked_sample_records:
            invalid_entries.append(
                f"{key}: tracked_ci_sample requires at least "
                f"{min_tracked_sample_records} records"
            )
        has_manifest_fixture = True

    return has_manifest_fixture


def _validate_required_fields(
    key: str, manifest_entry: dict[str, Any], invalid_entries: list[str]
) -> None:
    """Validate required fields."""
    for field in ("provenance", "owner", "last_refresh"):
        value = manifest_entry.get(field)
        if not isinstance(value, str) or not value.strip():
            invalid_entries.append(f"{key}: manifest.{field} is required")


def _validate_validation_status(
    key: str,
    manifest_entry: dict[str, Any],
    allowed_validation_statuses: set[str],
    invalid_entries: list[str],
) -> None:
    """Validate the validation status."""
    validation_status = manifest_entry.get("validation_status")
    if validation_status not in allowed_validation_statuses:
        invalid_entries.append(
            f"{key}: validation_status must be one of "
            f"{sorted(allowed_validation_statuses)}"
        )


def _validate_gap_entry(
    key: str,
    gaps: dict[str, dict[str, Any]],
    *,
    allowed_gap_statuses: set[str],
) -> list[str]:
    """Validate a gap entry."""
    if key not in gaps:
        return []

    gap = gaps[key]
    invalid_entries: list[str] = []

    _validate_gap_reason(key, gap, invalid_entries)
    _validate_gap_owner(key, gap, invalid_entries)
    _validate_gap_status(key, gap, allowed_gap_statuses, invalid_entries)
    _validate_gap_resolution_plan(key, gap, invalid_entries)
    _validate_de_scoped_gap_decision(key, gap, invalid_entries)

    return invalid_entries


def _validate_gap_reason(
    key: str, gap: dict[str, Any], invalid_entries: list[str]
) -> None:
    """Validate the gap reason."""
    if not isinstance(gap.get("reason"), str) or not gap.get("reason"):
        invalid_entries.append(f"{key}: gap.reason is required")


def _validate_gap_owner(
    key: str, gap: dict[str, Any], invalid_entries: list[str]
) -> None:
    """Validate the gap owner."""
    if not isinstance(gap.get("owner"), str) or not gap.get("owner"):
        invalid_entries.append(f"{key}: gap.owner is required")


def _validate_gap_status(
    key: str,
    gap: dict[str, Any],
    allowed_gap_statuses: set[str],
    invalid_entries: list[str],
) -> None:
    """Validate the gap status."""
    status = gap.get("status")
    if status not in allowed_gap_statuses:
        invalid_entries.append(
            f"{key}: gap.status must be one of {sorted(allowed_gap_statuses)}"
        )


def _validate_gap_resolution_plan(
    key: str, gap: dict[str, Any], invalid_entries: list[str]
) -> None:
    """Validate the gap resolution plan."""
    if not isinstance(gap.get("resolution_plan"), str) or not gap.get(
        "resolution_plan"
    ):
        invalid_entries.append(f"{key}: gap.resolution_plan is required")


def _validate_de_scoped_gap_decision(
    key: str, gap: dict[str, Any], invalid_entries: list[str]
) -> None:
    """Validate decision-recorded governance for replay fixture gaps."""
    if gap.get("status") != "decision_recorded":
        return
    if not isinstance(gap.get("de_scope_decision"), str) or not gap.get(
        "de_scope_decision"
    ):
        invalid_entries.append(f"{key}: gap.de_scope_decision is required")


def _fixture_coverage_findings(
    key: str,
    *,
    runtime_fixture_files: list[Path],
    runtime_fixture_lines: int,
    has_gap: bool,
    has_manifest_fixture: bool,
    min_recommended_records: int,
) -> tuple[list[str], list[str], list[str]]:
    missing_fixture: list[str] = []
    insufficient_fixture: list[str] = []
    stale_gap_entries: list[str] = []

    if not runtime_fixture_files and not has_manifest_fixture:
        if not has_gap:
            missing_fixture.append(
                f"{key}: no runtime fixture, no tracked fixture, and no GAP entry"
            )
    elif (
        runtime_fixture_files
        and runtime_fixture_lines < min_recommended_records
        and not (has_gap or has_manifest_fixture)
    ):
        insufficient_fixture.append(
            f"{key}: runtime fixture has < {min_recommended_records} records "
            f"(declare GAP or add records)"
        )

    if has_manifest_fixture and has_gap:
        stale_gap_entries.append(
            f"{key}: remove GAP entry (covered by tracked_ci_sample manifest)"
        )

    return missing_fixture, insufficient_fixture, stale_gap_entries


# ---------------------------------------------------------------------------
# INV-CFG-001: No legacy naming
# ---------------------------------------------------------------------------
class TestNoLegacyNaming:
    """INV-CFG-001: entity_type must use canonical names, paths must use
    canonical directory names (quality/ not dq/, filters/ not filter/)."""

    @pytest.fixture(scope="class")
    @classmethod
    def all_pipeline_configs(cls) -> list[tuple[Path, dict[str, Any]]]:
        return [(p, _load_yaml(p)) for p in _collect_pipeline_configs()]

    def test_no_legacy_entity_type(
        self, all_pipeline_configs: list[tuple[Path, dict[str, Any]]]
    ) -> None:
        """Pipeline configs must not use deprecated entity names (ADR-024)."""
        violations: list[str] = []
        for path, data in all_pipeline_configs:
            pipeline_cfg = data.get("pipeline")
            entity = (
                pipeline_cfg.get("entity_type", "")
                if isinstance(pipeline_cfg, dict)
                else ""
            )
            if entity in LEGACY_ENTITY_NAMES:
                violations.append(
                    f"{_rel(path)}: entity_type={entity!r} is legacy, "
                    f"use 'publication' variants instead"
                )
        assert not violations, "\n".join(violations)

    def test_no_legacy_path_fragments(
        self, all_pipeline_configs: list[tuple[Path, dict[str, Any]]]
    ) -> None:
        """Config values must not reference legacy directory names."""
        violations: list[str] = []
        for path, data in all_pipeline_configs:
            for legacy, canonical in LEGACY_PATH_FRAGMENTS:
                if _deep_string_search(data, legacy):
                    violations.append(
                        f"{_rel(path)}: contains legacy path {legacy!r}, "
                        f"use {canonical!r}"
                    )
        assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# INV-CFG-002: Schema / DQ / filter / source files exist
# ---------------------------------------------------------------------------
class TestConfigFilesExist:
    """INV-CFG-002: every unified entity must include required sections."""

    @pytest.fixture(scope="class")
    @classmethod
    def standard_pipelines(cls) -> list[tuple[str, str, Path, dict[str, Any]]]:
        """Return (provider, entity, path, raw) for unified entity configs."""
        result: list[tuple[str, str, Path, dict[str, Any]]] = []
        for path in _collect_pipeline_configs():
            data = _load_yaml(path)
            provider = str(data.get("provider", path.parent.name))
            entity = str(data.get("entity", path.stem))
            if provider == "composite":
                # Composite runtime is governed by configs/composites/*.yaml and
                # composite-specific bootstrap contracts, not the unified entity
                # schema/filters/contracts layout enforced for provider/entity
                # pipeline configs under configs/entities/**.
                continue
            result.append((provider, entity, path, data))
        return result

    def test_schema_section_exists(
        self, standard_pipelines: list[tuple[str, str, Path, dict[str, Any]]]
    ) -> None:
        """Each unified entity config must have schema section."""
        missing: list[str] = []
        for _provider, _entity, pipeline_path, data in standard_pipelines:
            if not isinstance(data.get("schema"), dict):
                missing.append(f"{_rel(pipeline_path)}: missing schema section")
        assert not missing, "\n".join(missing)

    def test_quality_section_exists(
        self, standard_pipelines: list[tuple[str, str, Path, dict[str, Any]]]
    ) -> None:
        """Each unified entity config must have quality section."""
        missing: list[str] = []
        for _provider, _entity, pipeline_path, data in standard_pipelines:
            if not isinstance(data.get("quality"), dict):
                missing.append(f"{_rel(pipeline_path)}: missing quality section")
        assert not missing, "\n".join(missing)

    def test_filter_section_exists(
        self, standard_pipelines: list[tuple[str, str, Path, dict[str, Any]]]
    ) -> None:
        """Each unified entity config must have filters section."""
        missing: list[str] = []
        for _provider, _entity, pipeline_path, data in standard_pipelines:
            if not isinstance(data.get("filters"), dict):
                missing.append(f"{_rel(pipeline_path)}: missing filters section")
        assert not missing, "\n".join(missing)

    def test_contracts_section_exists(
        self, standard_pipelines: list[tuple[str, str, Path, dict[str, Any]]]
    ) -> None:
        """Each unified entity config must have contracts section."""
        missing: list[str] = []
        for _provider, _entity, pipeline_path, data in standard_pipelines:
            if not isinstance(data.get("contracts"), dict):
                missing.append(f"{_rel(pipeline_path)}: missing contracts section")
        assert not missing, "\n".join(missing)

    def test_runtime_config_primary_keys_match_contract_policy(
        self, standard_pipelines: list[tuple[str, str, Path, dict[str, Any]]]
    ) -> None:
        """Loaded runtime config keys must match the typed contract policy."""
        violations: list[str] = []
        load_pipeline_contract_policy.cache_clear()
        for provider, entity, pipeline_path, data in standard_pipelines:
            pipeline = data.get("pipeline")
            if not isinstance(pipeline, dict):
                violations.append(f"{_rel(pipeline_path)}: missing pipeline section")
                continue
            pipeline_name = str(pipeline.get("pipeline_name") or "").strip()
            expected_keys = [
                str(key) for key in pipeline.get("business_primary_keys", [])
            ]
            runtime_config = load_pipeline_config_from_root(
                pipeline_name,
                configs_root=CONFIGS_DIR,
            )
            policy = load_pipeline_contract_policy(provider, entity)
            if list(runtime_config.business_primary_keys or []) != expected_keys:
                violations.append(
                    f"{_rel(pipeline_path)}: runtime business_primary_keys "
                    "do not match YAML pipeline.business_primary_keys"
                )
            if (
                policy.primary_key != expected_keys
                or policy.merge_keys != expected_keys
            ):
                violations.append(
                    f"{_rel(pipeline_path)}: contract primary_key/merge_keys "
                    "do not match pipeline.business_primary_keys"
                )
            if policy.contract_ref != f"{provider}.{entity}":
                violations.append(
                    f"{_rel(pipeline_path)}: contract_ref={policy.contract_ref!r} "
                    f"does not match {provider}.{entity!s}"
                )
        assert not violations, "\n".join(violations)

    def test_source_config_exists(
        self, standard_pipelines: list[tuple[str, str, Path, dict[str, Any]]]
    ) -> None:
        """Each provider used in entities must have provider config."""
        providers_seen: set[str] = set()
        missing: list[str] = []
        for provider, _entity, _path, _data in standard_pipelines:
            if provider in providers_seen:
                continue
            providers_seen.add(provider)
            provider_path = PROVIDERS_DIR / f"{provider}.yaml"
            if not provider_path.exists():
                missing.append(f"Missing provider config: {_rel(provider_path)}")
        assert not missing, "\n".join(missing)


class TestConfigContractSourceOfTruth:
    """Config CI contract must stay shared across scripts, tests, and wrappers."""

    def test_check_config_invariants_imports_shared_contract(self) -> None:
        """Pre-commit hook must reuse the shared config contract constants."""
        assert invariant_script.PIPELINE_ALLOWED_KEYS is PIPELINE_ALLOWED_KEYS
        assert invariant_script.ENTITY_ALLOWED_KEYS is ENTITY_ALLOWED_KEYS
        assert invariant_script.COMPOSITE_ALLOWED_KEYS is COMPOSITE_ALLOWED_KEYS
        assert invariant_script.PROVIDER_ALLOWED_KEYS is PROVIDER_ALLOWED_KEYS
        assert invariant_script.QUALITY_ALLOWED_KEYS is QUALITY_ALLOWED_KEYS
        assert invariant_script.FILTER_ALLOWED_KEYS is FILTER_ALLOWED_KEYS
        assert invariant_script.CONTRACT_ALLOWED_KEYS is CONTRACT_ALLOWED_KEYS
        assert invariant_script.REQUIRED_ENTITY_SECTIONS is REQUIRED_ENTITY_SECTIONS
        assert invariant_script.PROVIDER_AUTH_REQUIREMENTS is PROVIDER_AUTH_REQUIREMENTS
        assert invariant_script.VALID_LOADING_STRATEGIES is VALID_LOADING_STRATEGIES

    def test_check_config_invariants_parse_gate_includes_contract_yaml(self) -> None:
        """The fail-fast YAML parse gate must include contract config surfaces."""
        paths = set(invariant_script._config_governance_yaml_paths())
        assert CONFIGS_DIR / "contracts" / "chembl" / "activity.yaml" in paths

    def test_check_config_invariants_reports_malformed_yaml(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Malformed config YAML should fail before downstream config loaders run."""
        broken = tmp_path / "broken.yaml"
        broken.write_text("key: [\n", encoding="utf-8")
        monkeypatch.setattr(
            invariant_script,
            "_config_governance_yaml_paths",
            lambda: [broken],
        )

        errors = invariant_script.check_inv_000(verbose=False)

        assert len(errors) == 1
        assert "INV-CFG-000" in errors[0]
        assert "YAML parse error" in errors[0]

    def test_retired_pipeline_keys_are_not_part_of_active_ci_contract(self) -> None:
        """Retired keys must stay rejected by the active CI contract."""
        overlap = RETIRED_PIPELINE_KEYS & PIPELINE_ALLOWED_KEYS
        assert not overlap, (
            "Retired pipeline keys must not remain in PIPELINE_ALLOWED_KEYS: "
            f"{sorted(overlap)}"
        )

    def test_transitional_pipeline_keys_stay_explicitly_allowed(self) -> None:
        """Transitional aliases must remain explicit until the migration ends."""
        missing = TRANSITIONAL_PIPELINE_KEYS - PIPELINE_ALLOWED_KEYS
        assert not missing, (
            "Transitional pipeline keys must stay explicit in the active CI "
            f"contract until removed intentionally: {sorted(missing)}"
        )

    def test_validate_configs_wrapper_points_to_existing_canonical_script(self) -> None:
        """Supported validate-configs wrapper must keep pointing to a real script."""
        script = _canonical_script()
        assert script.exists(), f"Canonical validate-configs script missing: {script}"

    def test_required_filter_script_targets_real_entity_configs(self) -> None:
        """Required-fields CI gate must inspect the same entity config set."""
        script_paths = required_filter_script._entity_configs()
        test_paths = _collect_pipeline_configs()
        assert script_paths == test_paths

    def test_optionality_audit_script_targets_real_entity_configs(self) -> None:
        """Optionality audit gate must inspect the same entity config set."""
        script_paths = optionality_audit_script._entity_configs()
        test_paths = _collect_pipeline_configs()
        assert script_paths == test_paths


# ---------------------------------------------------------------------------
# INV-CFG-007: Explicit YAML requiredness must be mirrored in silver filters
# ---------------------------------------------------------------------------
class TestSilverRequiredFieldsCoverage:
    """INV-CFG-007: silver_filters.required_fields cover YAML required/not-null fields."""

    def test_explicit_required_fields_are_covered_by_silver_filters(self) -> None:
        violations = required_filter_script.collect_required_field_coverage_violations(
            _collect_pipeline_configs()
        )
        assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# INV-CFG-007A: Silver filters are structural-only in active config YAML
# ---------------------------------------------------------------------------
class TestSilverSemanticFilterHardGuard:
    """INV-CFG-007A: active silver_filters must not contain semantic buckets."""

    def test_no_semantic_silver_filter_keys_in_active_configs(self) -> None:
        violations: list[str] = []
        for path, section_name, filters in _collect_filter_sections():
            silver_filters = filters.get("silver_filters")
            if not isinstance(silver_filters, dict):
                continue
            for key in sorted(SEMANTIC_SILVER_FILTER_KEYS):
                if key in silver_filters:
                    violations.append(
                        f"{_rel(path)}:{section_name}.silver_filters.{key}"
                    )

        assert not violations, (
            "Semantic filters are forbidden under active silver_filters; "
            "move them to gold_filters or source_profile:\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# INV-CFG-007B: Gold filters are evaluated against pre-Gold/Silver field shape
# ---------------------------------------------------------------------------
class TestGoldFilterFieldShape:
    """INV-CFG-007B: gold_filters.required_fields use pre-Gold/Silver fields."""

    def test_chembl_assay_gold_filter_uses_silver_description_field(self) -> None:
        config_path = ENTITIES_DIR / "chembl" / "assay.yaml"
        filters = _load_yaml(config_path).get("filters", {})
        assert isinstance(filters, dict)
        gold_filters = filters.get("gold_filters", {})
        assert isinstance(gold_filters, dict)

        required_fields = gold_filters.get("required_fields", [])

        assert "assay_description" in required_fields
        assert "description" not in required_fields

    def test_gold_filter_ranges_reference_declared_schema_fields(self) -> None:
        """Range filters must name a field declared on the entity schema."""
        violations: list[str] = []
        for path in sorted(ENTITIES_DIR.glob("*/*.yaml")):
            data = _load_yaml(path)
            filters = data.get("filters")
            if not isinstance(filters, dict):
                continue
            gold_filters = filters.get("gold_filters")
            if not isinstance(gold_filters, dict):
                continue
            ranges = gold_filters.get("ranges")
            if not isinstance(ranges, dict) or not ranges:
                continue
            declared = _declared_entity_fields(data)
            unknown = sorted(name for name in ranges if name not in declared)
            if unknown:
                violations.append(
                    f"{_rel(path)}: gold_filters.ranges {unknown} not declared "
                    f"in schema.column_groups or quality field validations"
                )
        assert not violations, "\n".join(violations)

    def test_assay_parameters_url_patterns_match_non_whitespace(self) -> None:
        """YAML single-quoted [^\\\\s] must not leak a backslash/s class."""
        data = _load_yaml(ENTITIES_DIR / "chembl" / "assay_parameters.yaml")
        quality = data.get("quality")
        assert isinstance(quality, dict)
        patterns = [
            rule["pattern"]
            for rule in quality.get("entity_field_validations") or []
            if isinstance(rule, dict) and isinstance(rule.get("pattern"), str)
        ]
        assert patterns
        url_patterns = [pattern for pattern in patterns if "https?" in pattern]
        assert url_patterns
        for pattern in url_patterns:
            assert r"[^\s]" in pattern
            assert r"[^\\s]" not in pattern
            compiled = re.compile(pattern)
            assert compiled.fullmatch("https://example.org/unit")
            assert compiled.fullmatch("https://example.org/unit with-space") is None


def _declared_entity_fields(data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    schema = data.get("schema")
    if isinstance(schema, dict):
        for group in schema.get("column_groups") or []:
            if not isinstance(group, dict):
                continue
            for field in group.get("fields") or []:
                if isinstance(field, str):
                    names.add(field)
    quality = data.get("quality")
    if isinstance(quality, dict):
        for key in ("validations", "entity_field_validations", "field_validations"):
            for rule in quality.get(key) or []:
                if isinstance(rule, dict) and isinstance(rule.get("field"), str):
                    names.add(rule["field"])
    return names


# ---------------------------------------------------------------------------
# INV-CFG-007C: extraction_params stay entity-scoped (no cross-pipeline bleed)
# ---------------------------------------------------------------------------
class TestExtractionParamsAllowlist:
    """INV-CFG-007C: filters.extraction_params must not leak across entities."""

    def test_entity_extraction_params_match_allowlist(self) -> None:
        violations: list[str] = []
        for path in sorted(ENTITIES_DIR.glob("*/*.yaml")):
            rel_key = f"{path.parent.name}/{path.stem}"
            allowed = EXTRACTION_PARAM_ALLOWLIST.get(rel_key)
            if allowed is None:
                continue
            filters = _load_yaml(path).get("filters")
            if not isinstance(filters, dict):
                continue
            extraction = filters.get("extraction_params")
            if not isinstance(extraction, dict) or not extraction:
                continue
            extra = sorted(set(extraction) - allowed)
            if extra:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}: unexpected extraction_params "
                    f"{extra}; allowed={sorted(allowed)}"
                )
        assert not violations, "\n".join(violations)

    def test_non_empty_extraction_params_have_source_profile_metadata(self) -> None:
        """Source-side narrowing requires explicit baseline source-profile metadata."""
        violations: list[str] = []
        for path in sorted(ENTITIES_DIR.glob("*/*.yaml")):
            filters = _load_yaml(path).get("filters")
            if not isinstance(filters, dict):
                continue
            extraction = filters.get("extraction_params")
            if not isinstance(extraction, dict) or not extraction:
                continue
            source_profile = filters.get("source_profile")
            if not isinstance(source_profile, dict):
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}: missing filters.source_profile"
                )
                continue
            profile_id = source_profile.get("profile_id")
            version = source_profile.get("version")
            status = source_profile.get("status")
            declared_hash = source_profile.get("extraction_params_sha256")
            actual_hash = compute_extraction_params_sha256(extraction)
            if not isinstance(profile_id, str) or not profile_id:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}: source_profile.profile_id missing"
                )
            if not isinstance(version, str) or not version:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}: source_profile.version missing"
                )
            if status != "baseline":
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}: source_profile.status={status!r}"
                )
            if declared_hash != actual_hash:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}: source_profile hash mismatch "
                    f"declared={declared_hash!r} actual={actual_hash!r}"
                )
        assert not violations, "\n".join(violations)

    def test_non_allowlisted_entities_keep_extraction_params_empty(self) -> None:
        """Entities without an allowlist must not carry server-side extraction params."""
        violations: list[str] = []
        for path in sorted(ENTITIES_DIR.glob("*/*.yaml")):
            rel_key = f"{path.parent.name}/{path.stem}"
            if rel_key in EXTRACTION_PARAM_ALLOWLIST:
                continue
            filters = _load_yaml(path).get("filters")
            if not isinstance(filters, dict):
                continue
            extraction = filters.get("extraction_params")
            if isinstance(extraction, dict) and extraction:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}: extraction_params={sorted(extraction)}"
                )
        assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# INV-CFG-008: effective_optional_v1 must match current config surface
# ---------------------------------------------------------------------------
class TestEffectiveOptionalityResolution:
    """INV-CFG-008: resolved optionality mirrors current YAML config signals."""

    def test_resolved_optionality_matches_current_config_surface(self) -> None:
        violations = optionality_audit_script.collect_optionality_resolution_violations(
            _collect_pipeline_configs()
        )
        assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# INV-CFG-003: Valid loading_strategy
# ---------------------------------------------------------------------------
class TestValidLoadingStrategy:
    """INV-CFG-003: loading_strategy must be null or 'full_scan_only'."""

    @pytest.mark.parametrize("config_path", _collect_pipeline_configs(), ids=_rel)
    def test_loading_strategy_value(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        pipeline_cfg = data.get("pipeline")
        strategy = (
            pipeline_cfg.get("loading_strategy")
            if isinstance(pipeline_cfg, dict)
            else None
        )
        if strategy is not None:
            assert strategy in VALID_LOADING_STRATEGIES, (
                f"{_rel(config_path)}: loading_strategy={strategy!r} "
                f"is not valid. Allowed: {VALID_LOADING_STRATEGIES}"
            )


# ---------------------------------------------------------------------------
# INV-CFG-004: Config-bound authentication requirements
# ---------------------------------------------------------------------------
class TestProviderAuthRequirements:
    """INV-CFG-004: config-bound auth must declare env-var references."""

    @pytest.mark.parametrize(
        "provider,required_keys",
        list(PROVIDER_AUTH_REQUIREMENTS.items()),
        ids=list(PROVIDER_AUTH_REQUIREMENTS),
    )
    def test_source_has_auth_keys(
        self, provider: str, required_keys: list[str]
    ) -> None:
        provider_path = PROVIDERS_DIR / f"{provider}.yaml"
        if not provider_path.exists():
            pytest.skip(f"No provider config for {provider}")
        text = provider_path.read_text(encoding="utf-8")

        found = [key for key in required_keys if key in text]
        assert found, (
            f"{provider}: config must declare at least one of "
            f"{required_keys} for authentication. None found in file."
        )


# ---------------------------------------------------------------------------
# INV-CFG-005: No unknown top-level keys
# ---------------------------------------------------------------------------
class TestNoUnknownKeys:
    """INV-CFG-005: config files must not contain unrecognized top-level keys."""

    @pytest.mark.parametrize("config_path", _collect_pipeline_configs(), ids=_rel)
    def test_entity_top_level_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        unknown = set(data.keys()) - ENTITY_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown top-level keys: {unknown}. "
            f"Allowed: {sorted(ENTITY_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_pipeline_configs(), ids=_rel)
    def test_pipeline_section_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        pipeline_cfg = data.get("pipeline")
        if not isinstance(pipeline_cfg, dict):
            pytest.fail(f"{_rel(config_path)}: missing pipeline section")
        unknown = set(pipeline_cfg.keys()) - PIPELINE_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown pipeline section keys: {unknown}. "
            f"Allowed: {sorted(PIPELINE_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_pipeline_configs(), ids=_rel)
    def test_quality_section_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        quality_cfg = data.get("quality")
        if not isinstance(quality_cfg, dict):
            pytest.fail(f"{_rel(config_path)}: missing quality section")
        unknown = set(quality_cfg.keys()) - QUALITY_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown quality section keys: {unknown}. "
            f"Allowed: {sorted(QUALITY_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_pipeline_configs(), ids=_rel)
    def test_filters_section_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        filters_cfg = data.get("filters")
        if not isinstance(filters_cfg, dict):
            pytest.fail(f"{_rel(config_path)}: missing filters section")
        unknown = set(filters_cfg.keys()) - FILTER_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown filters section keys: {unknown}. "
            f"Allowed: {sorted(FILTER_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_pipeline_configs(), ids=_rel)
    def test_contracts_section_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        contracts_cfg = data.get("contracts")
        if not isinstance(contracts_cfg, dict):
            pytest.fail(f"{_rel(config_path)}: missing contracts section")
        unknown = set(contracts_cfg.keys()) - CONTRACT_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown contracts section keys: {unknown}. "
            f"Allowed: {sorted(CONTRACT_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_composite_configs(), ids=_rel)
    def test_composite_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        unknown = set(data.keys()) - COMPOSITE_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown top-level keys: {unknown}. "
            f"Allowed: {sorted(COMPOSITE_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_provider_configs(), ids=_rel)
    def test_provider_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        unknown = set(data.keys()) - PROVIDER_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown top-level keys: {unknown}. "
            f"Allowed: {sorted(PROVIDER_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_provider_configs(), ids=_rel)
    def test_provider_quality_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        quality_cfg = data.get("quality")
        if not isinstance(quality_cfg, dict):
            pytest.skip(f"{_rel(config_path)}: provider config has no quality section")
        unknown = set(quality_cfg.keys()) - QUALITY_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown provider quality keys: {unknown}. "
            f"Allowed: {sorted(QUALITY_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_provider_configs(), ids=_rel)
    def test_provider_filters_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        filters_cfg = data.get("filters")
        if not isinstance(filters_cfg, dict):
            pytest.skip(f"{_rel(config_path)}: provider config has no filters section")
        unknown = set(filters_cfg.keys()) - FILTER_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown provider filters keys: {unknown}. "
            f"Allowed: {sorted(FILTER_ALLOWED_KEYS)}"
        )


# ---------------------------------------------------------------------------
# INV-CFG-006: pipeline_name == {provider}_{entity_type}
# ---------------------------------------------------------------------------
class TestPipelineNameConvention:
    """INV-CFG-006: pipeline_name must equal {provider}_{entity_type}."""

    @pytest.mark.parametrize(
        "config_path",
        _collect_pipeline_configs(),
        ids=lambda p: _rel(p),
    )
    def test_pipeline_name_matches_convention(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        pipeline_cfg = data.get("pipeline")
        if not isinstance(pipeline_cfg, dict):
            pytest.fail(f"{_rel(config_path)}: missing pipeline section")
        name = pipeline_cfg.get("pipeline_name", "")
        provider = pipeline_cfg.get("provider", data.get("provider", ""))
        entity = pipeline_cfg.get("entity_type", data.get("entity", ""))
        expected = f"{provider}_{entity}"
        assert name == expected, (
            f"{_rel(config_path)}: pipeline_name={name!r} does not match "
            f"expected {expected!r} ({provider=}, {entity=})"
        )


# ---------------------------------------------------------------------------
# INV-CFG-007: SCD2 candidates must declare explicit Gold SCD2 policy
# ---------------------------------------------------------------------------
class TestExplicitGoldScd2Policy:
    """INV-CFG-007: SCD2 candidates must declare explicit canonical Gold policy."""

    @staticmethod
    def _load_effective_pipeline(config_path: Path) -> dict[str, Any]:
        data = _load_yaml(config_path)
        provider = str(data.get("provider", "")).strip()
        entity = str(data.get("entity", "")).strip()
        if not provider or not entity:
            pytest.fail(
                f"{_rel(config_path)}: missing provider/entity for effective config load"
            )
        return load_pipeline_config_from_root(
            f"{provider}_{entity}",
            configs_root=CONFIGS_DIR,
        ).model_dump(mode="python")

    @pytest.mark.parametrize("config_path", SCD2_CANDIDATE_CONFIGS, ids=_rel)
    def test_scd2_candidates_use_explicit_gold_scd2_policy(
        self, config_path: Path
    ) -> None:
        pipeline_cfg = self._load_effective_pipeline(config_path)
        sink_cfg = pipeline_cfg.get("sink")
        if not isinstance(sink_cfg, dict):
            pytest.fail(f"{_rel(config_path)}: missing pipeline.sink section")

        gold_cfg = sink_cfg.get("gold")
        if not isinstance(gold_cfg, dict):
            pytest.fail(f"{_rel(config_path)}: missing pipeline.sink.gold section")

        mode = gold_cfg.get("mode")
        assert mode == "scd2", (
            f"{_rel(config_path)}: SCD2 candidate must declare "
            f"pipeline.sink.gold.mode='scd2', found {mode!r}"
        )

        scd_config = gold_cfg.get("scd_config")
        assert isinstance(scd_config, dict), (
            f"{_rel(config_path)}: SCD2 candidate must declare "
            "pipeline.sink.gold.scd_config"
        )

        missing = REQUIRED_SCD_CONFIG_KEYS - set(scd_config)
        assert not missing, (
            f"{_rel(config_path)}: scd_config missing canonical keys {sorted(missing)}"
        )

        legacy = LEGACY_SCD_CONFIG_KEYS & set(scd_config)
        assert not legacy, (
            f"{_rel(config_path)}: scd_config uses legacy alias keys {sorted(legacy)}"
        )

        blank_values = [
            key
            for key in REQUIRED_SCD_CONFIG_KEYS
            if not isinstance(scd_config.get(key), str) or not scd_config[key].strip()
        ]
        assert not blank_values, (
            f"{_rel(config_path)}: scd_config keys must be non-empty strings: "
            f"{sorted(blank_values)}"
        )


# ---------------------------------------------------------------------------
# INV-CFG-008: Contract hash_exclude alignment with META_FIELDS
# ---------------------------------------------------------------------------
class TestContractHashExcludeInvariants:
    """INV-CFG-008: contracts.hash_exclude must use canonical metadata fields."""

    _REQUIRED_EXCLUDES: set[str] = {
        "_ingestion_ts",
        "_run_id",
        "_run_type",
        "_dq_error",
        "_dq_warn",
    }
    _LEGACY_EXCLUDES: set[str] = {"_dq_errors", "_dq_status"}

    @staticmethod
    def _root_hash_policy_exclude_fields(data: dict[str, Any]) -> set[str]:
        """Return explicit hash_policy exclude_fields when root hash_policy is present."""
        root = data.get("hash_policy")
        if not isinstance(root, dict):
            return set()
        nested = root.get("hash_policy")
        if not isinstance(nested, dict):
            return set()
        exclude_fields = nested.get("exclude_fields")
        if not isinstance(exclude_fields, list):
            return set()
        return {str(item) for item in exclude_fields}

    def test_base_contract_defaults_hash_exclude(self) -> None:
        """Base contract defaults must be canonical and META_FIELDS-aligned."""
        base_path = CONFIGS_DIR / "base" / "pipeline.yaml"
        data = _load_yaml(base_path)
        defaults = data.get("contract_defaults")
        if not isinstance(defaults, dict):
            pytest.fail(f"{_rel(base_path)}: missing contract_defaults section")

        hash_exclude = defaults.get("hash_exclude")
        if not isinstance(hash_exclude, list):
            pytest.fail(
                f"{_rel(base_path)}: contract_defaults.hash_exclude must be list"
            )

        exclude_set = {str(x) for x in hash_exclude}
        missing = self._REQUIRED_EXCLUDES - exclude_set
        legacy = self._LEGACY_EXCLUDES & exclude_set
        non_meta = exclude_set - META_FIELDS

        assert not missing, (
            f"{_rel(base_path)}: contract_defaults.hash_exclude missing {sorted(missing)}"
        )
        assert not legacy, (
            f"{_rel(base_path)}: contract_defaults.hash_exclude uses legacy keys "
            f"{sorted(legacy)}"
        )
        assert not non_meta, (
            f"{_rel(base_path)}: contract_defaults.hash_exclude has non-meta keys "
            f"{sorted(non_meta)} (expected subset of META_FIELDS)"
        )

    @pytest.mark.parametrize("config_path", _collect_pipeline_configs(), ids=_rel)
    def test_entity_contract_hash_exclude(self, config_path: Path) -> None:
        """Each entity's effective hash_exclude must be canonical and policy-aligned."""
        data = _load_yaml(config_path)
        provider = str(data.get("provider", "")).strip()
        entity = str(data.get("entity", "")).strip()
        if not provider or not entity:
            pytest.fail(
                f"{_rel(config_path)}: missing provider/entity for contract policy load"
            )

        load_pipeline_contract_policy.cache_clear()
        policy = load_pipeline_contract_policy(provider, entity)
        exclude_set = {str(x) for x in policy.hash_exclude}
        missing = self._REQUIRED_EXCLUDES - exclude_set
        legacy = self._LEGACY_EXCLUDES & exclude_set
        non_meta = exclude_set - META_FIELDS
        allowed_non_meta = self._root_hash_policy_exclude_fields(data) - META_FIELDS
        unexpected_non_meta = non_meta - allowed_non_meta

        assert not missing, (
            f"{_rel(config_path)}: contracts.hash_exclude missing {sorted(missing)}"
        )
        assert not legacy, (
            f"{_rel(config_path)}: contracts.hash_exclude uses legacy keys "
            f"{sorted(legacy)}"
        )
        assert not unexpected_non_meta, (
            f"{_rel(config_path)}: contracts.hash_exclude has non-meta keys "
            f"{sorted(unexpected_non_meta)} (expected META_FIELDS or hash_policy.exclude_fields)"
        )


# ---------------------------------------------------------------------------
# INV-CFG-008: Bronze fixture coverage (input fixture or explicit GAP)
# ---------------------------------------------------------------------------
class TestBronzeFixtureCoverage:
    """INV-CFG-008: each pipeline must have Bronze input fixture or explicit GAP."""

    _MIN_RECOMMENDED_RECORDS = 200
    _MIN_TRACKED_SAMPLE_RECORDS = 20
    _ALLOWED_GAP_STATUS = {"open", "in_progress", "blocked", "decision_recorded"}
    _ACTIVE_GAP_STATUS = {"open", "in_progress"}
    _MAX_BLOCKED_GAPS = 0
    _MAX_DECISION_RECORDED_GAPS = 0
    _ALLOWED_FIXTURE_KINDS = {
        "tracked_ci_sample",
        "tracked_edge_case_sample",
        "local_runtime_snapshot",
    }
    _ALLOWED_VALIDATION_STATUSES = {"valid", "provisional", "stale"}

    def test_bronze_fixture_gap_registry_exists(self) -> None:
        assert BRONZE_FIXTURE_GAPS_PATH.exists(), (
            f"Missing gap registry: {_rel(BRONZE_FIXTURE_GAPS_PATH)}"
        )

    def test_bronze_fixture_manifest_exists(self) -> None:
        assert BRONZE_FIXTURE_MANIFEST_PATH.exists(), (
            f"Missing fixture manifest: {_rel(BRONZE_FIXTURE_MANIFEST_PATH)}"
        )

    def test_tracked_fixture_manifest_has_representative_baseline(self) -> None:
        manifest = _load_bronze_fixture_manifest()
        tracked = [
            key
            for key, entry in manifest.items()
            if entry.get("fixture_kind") == "tracked_ci_sample"
            and entry.get("validation_status") == "valid"
        ]
        assert len(tracked) >= 4, (
            "Fixture manifest must include at least 4 valid tracked_ci_sample "
            f"entries, found {len(tracked)}: {sorted(tracked)}"
        )

    def test_bronze_fixture_gaps_are_ratchet_only(self) -> None:
        gaps = _load_bronze_fixture_gaps()

        active = sorted(
            key
            for key, gap in gaps.items()
            if gap.get("status") in self._ACTIVE_GAP_STATUS
        )
        blocked = sorted(
            key for key, gap in gaps.items() if gap.get("status") == "blocked"
        )
        decision_recorded = sorted(
            key for key, gap in gaps.items() if gap.get("status") == "decision_recorded"
        )

        assert not active, (
            "bronze_fixture_gaps.yaml must not carry active open/in_progress "
            f"replay debt; close with tracked fixture evidence or explicitly "
            f"de-scope: {active}"
        )
        assert len(blocked) <= self._MAX_BLOCKED_GAPS, (
            "Blocked Bronze fixture gaps require an explicit budget change; "
            f"max={self._MAX_BLOCKED_GAPS}, found={len(blocked)}: {blocked}"
        )
        assert len(decision_recorded) <= self._MAX_DECISION_RECORDED_GAPS, (
            "Decision-recorded Bronze fixture gaps are residual replay evidence "
            "debt and may only grow through an explicit budget change; "
            f"max={self._MAX_DECISION_RECORDED_GAPS}, found={len(decision_recorded)}: "
            f"{decision_recorded}"
        )

    def test_bronze_fixture_coverage(self) -> None:
        gaps = _load_bronze_fixture_gaps()
        manifest = _load_bronze_fixture_manifest()

        pipeline_keys: set[str] = set()
        missing_fixture: list[str] = []
        insufficient_fixture: list[str] = []
        invalid_gap_entries: list[str] = []
        invalid_manifest_entries: list[str] = []
        stale_gap_entries: list[str] = []

        for config_path in _collect_pipeline_configs():
            (
                key,
                _provider,
                _entity,
                runtime_fixture_files,
                runtime_fixture_lines,
            ) = _pipeline_fixture_context(config_path)
            pipeline_keys.add(key)
            has_gap = key in gaps
            manifest_entry = manifest.get(key)
            manifest_errors, has_manifest_fixture = _validate_manifest_entry(
                key,
                manifest_entry,
                allowed_fixture_kinds=self._ALLOWED_FIXTURE_KINDS,
                allowed_validation_statuses=self._ALLOWED_VALIDATION_STATUSES,
                min_tracked_sample_records=self._MIN_TRACKED_SAMPLE_RECORDS,
            )
            invalid_manifest_entries.extend(manifest_errors)
            invalid_gap_entries.extend(
                _validate_gap_entry(
                    key,
                    gaps,
                    allowed_gap_statuses=self._ALLOWED_GAP_STATUS,
                )
            )
            missing, insufficient, stale = _fixture_coverage_findings(
                key,
                runtime_fixture_files=runtime_fixture_files,
                runtime_fixture_lines=runtime_fixture_lines,
                has_gap=has_gap,
                has_manifest_fixture=has_manifest_fixture,
                min_recommended_records=self._MIN_RECOMMENDED_RECORDS,
            )
            missing_fixture.extend(missing)
            insufficient_fixture.extend(insufficient)
            stale_gap_entries.extend(stale)

        unknown_gap_keys = sorted(set(gaps) - pipeline_keys)
        unknown_manifest_keys = sorted(set(manifest) - pipeline_keys)
        assert not unknown_gap_keys, (
            f"{_rel(BRONZE_FIXTURE_GAPS_PATH)} contains unknown pipeline keys: "
            f"{unknown_gap_keys}"
        )
        assert not unknown_manifest_keys, (
            f"{_rel(BRONZE_FIXTURE_MANIFEST_PATH)} contains unknown pipeline keys: "
            f"{unknown_manifest_keys}"
        )
        assert not missing_fixture, "\n".join(missing_fixture)
        assert not insufficient_fixture, "\n".join(insufficient_fixture)
        assert not invalid_gap_entries, "\n".join(invalid_gap_entries)
        assert not invalid_manifest_entries, "\n".join(invalid_manifest_entries)
        assert not stale_gap_entries, "\n".join(stale_gap_entries)
