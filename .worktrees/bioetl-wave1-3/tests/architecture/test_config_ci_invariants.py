"""CI invariants for configs/** directory.

Ensures structural integrity of all YAML configuration files:
  INV-CFG-001: No legacy naming (document→publication, dq/→quality/, filter/→filters/)
  INV-CFG-002: Unified entity sections (schema/quality/filters/contracts) and provider config exist
  INV-CFG-003: loading_strategy is null or a valid LoadingStrategy enum value
  INV-CFG-004: Providers requiring auth declare API key / mailto env vars
  INV-CFG-005: No unknown keys in unified entity/composite/provider configs
  INV-CFG-006: pipeline_name matches {provider}_{entity_type} convention

Reference:
    ADR-024 (entity naming), ADR-027 (DQ externalization), ADR-028 (filter
    externalization), ADR-029 (convention-based path resolution), ADR-031
    (loading strategy).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.constants import META_FIELDS

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

# Providers that require authentication credentials in configs/providers/
# Maps provider -> list of required env-var keys (at least one must appear)
PROVIDER_AUTH_REQUIREMENTS: dict[str, list[str]] = {
    "openalex": ["mailto"],
    "crossref": ["mailto"],
    "pubmed": ["api_key_env", "email_env"],
}

VALID_LOADING_STRATEGIES: set[str] = {"full_scan_only"}

# Allowed top-level keys per config category.
# Derived from PipelineYamlConfig Pydantic model and existing YAML files.
PIPELINE_ALLOWED_KEYS: set[str] = {
    "pipeline_name",
    "provider",
    "entity_type",
    "version",
    "description",
    "batch_size",
    "filter_batch_size",
    "checkpoint_interval",
    "business_primary_keys",
    "technical_primary_key",
    "silver_table",
    "gold_table",
    "loading_strategy",
    "source",
    "sink",
    "dq_config_file",
    "dq_overrides",
    "circuit_breaker",
    "filter_config_file",
    "filter_rules",
    "column_groups_file",
    "data_schema_file",
    "column_groups",
    "input_filter",
    "silver_filters",
    "gold_filters",
    "maintenance",
    "transform",
    "extraction_params",
    "page_size_override",
    "schema_file",
}

ENTITY_ALLOWED_KEYS: set[str] = {
    "version",
    "provider",
    "entity",
    "pipeline",
    "schema",
    "quality",
    "filters",
    "contracts",
    "hash_policy",
}

COMPOSITE_ALLOWED_KEYS: set[str] = {
    "composite",
    "gold_filters",
    "silver_filters",
    "filter_config_file",
    "filter_rules",
    "maintenance",
}

PROVIDER_ALLOWED_KEYS: set[str] = {
    "version",
    "provider",
    "source",
    "quality",
    "filters",
    "entities",
    "entity_notes",
}

# Legacy entity names that MUST NOT appear in configs (ADR-024).
LEGACY_ENTITY_NAMES: set[str] = {"document", "document_similarity", "document_term"}

# Legacy path fragments that MUST NOT appear in any YAML value.
LEGACY_PATH_FRAGMENTS: list[tuple[str, str]] = [
    ("../../dq/", "../../quality/"),
    ("../../filter/", "../../filters/"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict on parse failure."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return {}
    return data


def _collect_pipeline_configs() -> list[Path]:
    """Collect all unified entity YAML configs."""
    return sorted(p for p in ENTITIES_DIR.rglob("*.yaml") if not p.name.startswith("_"))


def _collect_composite_configs() -> list[Path]:
    """Collect all composite YAML configs."""
    return sorted(
        p for p in COMPOSITES_DIR.glob("*.yaml") if not p.name.startswith("_")
    )


def _collect_provider_configs() -> list[Path]:
    """Collect unified provider YAML configs."""
    return sorted(p for p in PROVIDERS_DIR.glob("*.yaml") if not p.name.startswith("_"))


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


# ---------------------------------------------------------------------------
# INV-CFG-001: No legacy naming
# ---------------------------------------------------------------------------
class TestNoLegacyNaming:
    """INV-CFG-001: entity_type must use canonical names, paths must use
    canonical directory names (quality/ not dq/, filters/ not filter/)."""

    @pytest.fixture(scope="class")
    def all_pipeline_configs(self) -> list[tuple[Path, dict[str, Any]]]:
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
    def standard_pipelines(self) -> list[tuple[str, str, Path, dict[str, Any]]]:
        """Return (provider, entity, path, raw) for unified entity configs."""
        result: list[tuple[str, str, Path, dict[str, Any]]] = []
        for path in _collect_pipeline_configs():
            data = _load_yaml(path)
            provider = str(data.get("provider", path.parent.name))
            entity = str(data.get("entity", path.stem))
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
# INV-CFG-004: API key / mailto requirements
# ---------------------------------------------------------------------------
class TestProviderAuthRequirements:
    """INV-CFG-004: providers needing auth must declare env-var references."""

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
# INV-CFG-007: Contract hash_exclude alignment with META_FIELDS
# ---------------------------------------------------------------------------
class TestContractHashExcludeInvariants:
    """INV-CFG-007: contracts.hash_exclude must use canonical metadata fields."""

    _REQUIRED_EXCLUDES: set[str] = {
        "_ingestion_ts",
        "_run_id",
        "_run_type",
        "_dq_error",
        "_dq_warn",
    }
    _LEGACY_EXCLUDES: set[str] = {"_dq_errors", "_dq_status"}

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
        """Each entity contracts.hash_exclude must be canonical and META_FIELDS-aligned."""
        data = _load_yaml(config_path)
        contracts = data.get("contracts")
        if not isinstance(contracts, dict):
            pytest.fail(f"{_rel(config_path)}: missing contracts section")

        hash_exclude = contracts.get("hash_exclude")
        if not isinstance(hash_exclude, list):
            pytest.fail(f"{_rel(config_path)}: contracts.hash_exclude must be list")

        exclude_set = {str(x) for x in hash_exclude}
        missing = self._REQUIRED_EXCLUDES - exclude_set
        legacy = self._LEGACY_EXCLUDES & exclude_set
        non_meta = exclude_set - META_FIELDS

        assert not missing, (
            f"{_rel(config_path)}: contracts.hash_exclude missing {sorted(missing)}"
        )
        assert not legacy, (
            f"{_rel(config_path)}: contracts.hash_exclude uses legacy keys "
            f"{sorted(legacy)}"
        )
        assert not non_meta, (
            f"{_rel(config_path)}: contracts.hash_exclude has non-meta keys "
            f"{sorted(non_meta)} (expected subset of META_FIELDS)"
        )


# ---------------------------------------------------------------------------
# INV-CFG-008: Bronze fixture coverage (input fixture or explicit GAP)
# ---------------------------------------------------------------------------
class TestBronzeFixtureCoverage:
    """INV-CFG-008: each pipeline must have Bronze input fixture or explicit GAP."""

    _MIN_RECOMMENDED_RECORDS = 200

    def test_bronze_fixture_gap_registry_exists(self) -> None:
        assert BRONZE_FIXTURE_GAPS_PATH.exists(), (
            f"Missing gap registry: {_rel(BRONZE_FIXTURE_GAPS_PATH)}"
        )

    def test_bronze_fixture_coverage(self) -> None:
        gaps = _load_bronze_fixture_gaps()

        pipeline_keys: set[str] = set()
        missing_fixture: list[str] = []
        insufficient_fixture: list[str] = []
        invalid_gap_entries: list[str] = []

        for config_path in _collect_pipeline_configs():
            data = _load_yaml(config_path)
            provider = str(data.get("provider", config_path.parent.name))
            entity = str(data.get("entity", config_path.stem))
            key = f"{provider}/{entity}"
            pipeline_keys.add(key)

            fixture_files = _collect_input_jsonl_files(provider, entity)
            fixture_lines = _count_jsonl_lines(
                fixture_files, stop_after=self._MIN_RECOMMENDED_RECORDS
            )
            has_gap = key in gaps

            if not fixture_files:
                if not has_gap:
                    missing_fixture.append(
                        f"{key}: no data/input/bronze fixture and no GAP entry"
                    )
            else:
                if fixture_lines < self._MIN_RECOMMENDED_RECORDS and not has_gap:
                    insufficient_fixture.append(
                        f"{key}: fixture has < {self._MIN_RECOMMENDED_RECORDS} records "
                        f"(declare GAP or add records)"
                    )

            if has_gap:
                gap = gaps[key]
                if not isinstance(gap.get("reason"), str) or not gap.get("reason"):
                    invalid_gap_entries.append(f"{key}: gap.reason is required")
                if not isinstance(gap.get("owner"), str) or not gap.get("owner"):
                    invalid_gap_entries.append(f"{key}: gap.owner is required")
                if not isinstance(gap.get("resolution_plan"), str) or not gap.get(
                    "resolution_plan"
                ):
                    invalid_gap_entries.append(
                        f"{key}: gap.resolution_plan is required"
                    )

        unknown_gap_keys = sorted(set(gaps) - pipeline_keys)
        assert not unknown_gap_keys, (
            f"{_rel(BRONZE_FIXTURE_GAPS_PATH)} contains unknown pipeline keys: "
            f"{unknown_gap_keys}"
        )
        assert not missing_fixture, "\n".join(missing_fixture)
        assert not insufficient_fixture, "\n".join(insufficient_fixture)
        assert not invalid_gap_entries, "\n".join(invalid_gap_entries)
