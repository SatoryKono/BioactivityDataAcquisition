"""CI invariants for configs/** directory.

Ensures structural integrity of all YAML configuration files:
  INV-CFG-001: No legacy naming (document→publication, dq/→quality/, filter/→filters/)
  INV-CFG-002: Schema/DQ/filter/source files exist for every pipeline
  INV-CFG-003: loading_strategy is null or a valid LoadingStrategy enum value
  INV-CFG-004: Providers requiring auth declare API key / mailto env vars
  INV-CFG-005: No unknown top-level keys in pipeline, source, quality, filter configs
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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = PROJECT_ROOT / "configs"
PIPELINES_DIR = CONFIGS_DIR / "pipelines"
SOURCES_DIR = CONFIGS_DIR / "sources"
QUALITY_DIR = CONFIGS_DIR / "quality"
FILTERS_DIR = CONFIGS_DIR / "filters"
SCHEMAS_DIR = CONFIGS_DIR / "schemas"

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

# Providers that require authentication credentials in configs/sources/
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
}

COMPOSITE_ALLOWED_KEYS: set[str] = {
    "composite",
    "gold_filters",
    "silver_filters",
    "filter_config_file",
    "filter_rules",
    "maintenance",
}

SOURCE_ALLOWED_KEYS: set[str] = {
    "source",
    "entities",
    "entity_notes",
}

QUALITY_ALLOWED_KEYS: set[str] = {
    "version",
    "provider",
    "entity",
    "thresholds",
    "strict_validation",
    "invalid_record_policy",
    "field_validations",
    "cross_field_validations",
    "conditional_validations",
    "report",
    "required_fields",
}

FILTER_ALLOWED_KEYS: set[str] = {
    "version",
    "provider",
    "entity",
    "input_filter",
    "silver_filters",
    "gold_filters",
    "extraction_params",
    "batch_size",
    "page_size",
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
    """Collect all entity-level pipeline YAML configs (skip _base.yaml)."""
    return sorted(
        p for p in PIPELINES_DIR.rglob("*.yaml") if not p.name.startswith("_")
    )


def _collect_source_configs() -> list[Path]:
    return sorted(SOURCES_DIR.glob("*.yaml"))


def _collect_quality_configs() -> list[Path]:
    return sorted(p for p in QUALITY_DIR.rglob("*.yaml") if not p.name.startswith("_"))


def _collect_filter_configs() -> list[Path]:
    return sorted(p for p in FILTERS_DIR.rglob("*.yaml") if not p.name.startswith("_"))


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
            entity = data.get("entity_type", "")
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
    """INV-CFG-002: every pipeline must have companion config files."""

    @pytest.fixture(scope="class")
    def standard_pipelines(self) -> list[tuple[str, str, Path]]:
        """Return (provider, entity, path) for non-composite pipelines."""
        result = []
        for p in _collect_pipeline_configs():
            if "composite" in p.parts:
                continue
            data = _load_yaml(p)
            provider = data.get("provider", p.parent.name)
            entity = data.get("entity_type", p.stem)
            result.append((provider, entity, p))
        return result

    def test_schema_file_exists(
        self, standard_pipelines: list[tuple[str, str, Path]]
    ) -> None:
        """Each pipeline must have a corresponding configs/schemas/{provider}/{entity}.yaml."""
        missing: list[str] = []
        for provider, entity, pipeline_path in standard_pipelines:
            schema_path = SCHEMAS_DIR / provider / f"{entity}.yaml"
            if not schema_path.exists():
                missing.append(
                    f"{_rel(pipeline_path)}: missing schema at {_rel(schema_path)}"
                )
        assert not missing, "\n".join(missing)

    def test_quality_config_exists(
        self, standard_pipelines: list[tuple[str, str, Path]]
    ) -> None:
        """Each pipeline must have a DQ config in configs/quality/entities/."""
        missing: list[str] = []
        for provider, entity, pipeline_path in standard_pipelines:
            dq_path = QUALITY_DIR / "entities" / provider / f"{entity}.yaml"
            if not dq_path.exists():
                missing.append(
                    f"{_rel(pipeline_path)}: missing DQ config at {_rel(dq_path)}"
                )
        assert not missing, "\n".join(missing)

    def test_filter_config_exists(
        self, standard_pipelines: list[tuple[str, str, Path]]
    ) -> None:
        """Each pipeline must have a filter config in configs/filters/entities/."""
        missing: list[str] = []
        for provider, entity, pipeline_path in standard_pipelines:
            filter_path = FILTERS_DIR / "entities" / provider / f"{entity}.yaml"
            if not filter_path.exists():
                missing.append(
                    f"{_rel(pipeline_path)}: missing filter config at "
                    f"{_rel(filter_path)}"
                )
        assert not missing, "\n".join(missing)

    def test_source_config_exists(
        self, standard_pipelines: list[tuple[str, str, Path]]
    ) -> None:
        """Each provider used in pipelines must have a source config."""
        providers_seen: set[str] = set()
        missing: list[str] = []
        for provider, _entity, _path in standard_pipelines:
            if provider in providers_seen:
                continue
            providers_seen.add(provider)
            source_path = SOURCES_DIR / f"{provider}.yaml"
            if not source_path.exists():
                missing.append(f"Missing source config: {_rel(source_path)}")
        assert not missing, "\n".join(missing)


# ---------------------------------------------------------------------------
# INV-CFG-003: Valid loading_strategy
# ---------------------------------------------------------------------------
class TestValidLoadingStrategy:
    """INV-CFG-003: loading_strategy must be null or 'full_scan_only'."""

    @pytest.mark.parametrize("config_path", _collect_pipeline_configs(), ids=_rel)
    def test_loading_strategy_value(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        strategy = data.get("loading_strategy")
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
        source_path = SOURCES_DIR / f"{provider}.yaml"
        if not source_path.exists():
            pytest.skip(f"No source config for {provider}")

        text = source_path.read_text(encoding="utf-8")

        found = [key for key in required_keys if key in text]
        assert found, (
            f"configs/sources/{provider}.yaml: must declare at least one of "
            f"{required_keys} for authentication. None found in file."
        )


# ---------------------------------------------------------------------------
# INV-CFG-005: No unknown top-level keys
# ---------------------------------------------------------------------------
class TestNoUnknownKeys:
    """INV-CFG-005: config files must not contain unrecognized top-level keys."""

    @pytest.mark.parametrize("config_path", _collect_pipeline_configs(), ids=_rel)
    def test_pipeline_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        is_composite = "composite" in config_path.parts
        allowed = COMPOSITE_ALLOWED_KEYS if is_composite else PIPELINE_ALLOWED_KEYS
        unknown = set(data.keys()) - allowed
        assert not unknown, (
            f"{_rel(config_path)}: unknown top-level keys: {unknown}. "
            f"Allowed: {sorted(allowed)}"
        )

    @pytest.mark.parametrize("config_path", _collect_source_configs(), ids=_rel)
    def test_source_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        unknown = set(data.keys()) - SOURCE_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown top-level keys: {unknown}. "
            f"Allowed: {sorted(SOURCE_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_quality_configs(), ids=_rel)
    def test_quality_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        unknown = set(data.keys()) - QUALITY_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown top-level keys: {unknown}. "
            f"Allowed: {sorted(QUALITY_ALLOWED_KEYS)}"
        )

    @pytest.mark.parametrize("config_path", _collect_filter_configs(), ids=_rel)
    def test_filter_keys(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        unknown = set(data.keys()) - FILTER_ALLOWED_KEYS
        assert not unknown, (
            f"{_rel(config_path)}: unknown top-level keys: {unknown}. "
            f"Allowed: {sorted(FILTER_ALLOWED_KEYS)}"
        )


# ---------------------------------------------------------------------------
# INV-CFG-006: pipeline_name == {provider}_{entity_type}
# ---------------------------------------------------------------------------
class TestPipelineNameConvention:
    """INV-CFG-006: pipeline_name must equal {provider}_{entity_type}."""

    @pytest.mark.parametrize(
        "config_path",
        [p for p in _collect_pipeline_configs() if "composite" not in p.parts],
        ids=lambda p: _rel(p),
    )
    def test_pipeline_name_matches_convention(self, config_path: Path) -> None:
        data = _load_yaml(config_path)
        name = data.get("pipeline_name", "")
        provider = data.get("provider", "")
        entity = data.get("entity_type", "")
        expected = f"{provider}_{entity}"
        assert name == expected, (
            f"{_rel(config_path)}: pipeline_name={name!r} does not match "
            f"expected {expected!r} ({provider=}, {entity=})"
        )
