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
"""Architecture guardrails for canonical vs compatibility config schema fields."""

from __future__ import annotations

import pytest

import json
import re
from pathlib import Path
from typing import Any

import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = PROJECT_ROOT / "configs" / "_schema"
CONFIG_README = PROJECT_ROOT / "configs" / "README.md"
PIPELINE_GUIDE = PROJECT_ROOT / "docs" / "03-guides" / "pipeline-configuration.md"
PROVIDERS_DIR = PROJECT_ROOT / "configs" / "providers"
ENTITIES_DIR = PROJECT_ROOT / "configs" / "entities"
COMPOSITES_DIR = PROJECT_ROOT / "configs" / "composites"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict), f"{path} must contain a YAML mapping"
    return payload


def test_pipeline_schema_does_not_advertise_retired_file_reference_keys() -> None:
    """Pipeline JSON schema must not expose retired legacy file-reference keys."""
    schema = _load_schema("pipeline.json")
    properties = schema.get("properties")
    assert isinstance(properties, dict), (
        "pipeline.json must contain top-level properties"
    )

    retired_keys = {
        "schema_file",
        "data_schema_file",
        "column_groups_file",
        "primary_keys",
    }
    present = sorted(retired_keys.intersection(properties))
    assert not present, (
        f"pipeline.json still advertises retired legacy file-reference keys: {present}"
    )


def test_pipeline_schema_does_not_advertise_filter_batch_size() -> None:
    """Pipeline JSON schema must not expose retired filter_batch_size."""
    schema = _load_schema("pipeline.json")
    properties = schema["properties"]
    assert "filter_batch_size" not in properties, (
        "pipeline.json still advertises retired filter_batch_size"
    )


def test_pipeline_source_schema_does_not_advertise_source_pagination_aliases() -> None:
    """Entity pipeline schema must not embed provider transport models."""
    schema = _load_schema("pipeline.json")
    defs = schema.get("$defs")
    assert isinstance(defs, dict), "pipeline.json must contain $defs section"
    assert "ProviderConfigYaml" not in defs, (
        "pipeline.json must not embed ProviderConfigYaml; provider transport "
        "belongs in source.json / configs/providers"
    )


def test_source_schema_does_not_advertise_retired_pagination_aliases() -> None:
    """Source JSON schema must not expose retired provider pagination aliases."""
    schema = _load_schema("source.json")
    defs = schema.get("$defs")
    assert isinstance(defs, dict), "source.json must contain $defs section"

    provider_cfg = defs.get("ProviderConfigYaml")
    assert isinstance(provider_cfg, dict), "source.json missing ProviderConfigYaml"

    properties = provider_cfg.get("properties")
    assert isinstance(properties, dict), "ProviderConfigYaml must define properties"

    forbidden = {"batch_size", "page_size", "max_url_length"}
    present = sorted(forbidden.intersection(properties))
    assert not present, (
        f"source.json still advertises retired provider pagination aliases: {present}"
    )


def test_source_schema_does_not_advertise_retired_root_batch_size() -> None:
    """Source JSON schema must not expose retired source.batch_size."""
    schema = _load_schema("source.json")
    defs = schema.get("$defs")
    assert isinstance(defs, dict), "source.json must contain $defs section"

    source_section = defs.get("SourceSectionConfig")
    assert isinstance(source_section, dict), "source.json missing SourceSectionConfig"

    properties = source_section.get("properties")
    assert isinstance(properties, dict), "SourceSectionConfig must define properties"

    assert "batch_size" not in properties, (
        "source.json still advertises retired source.batch_size"
    )


def test_pipeline_source_schema_does_not_advertise_secrets_or_transport() -> None:
    """Entity pipeline.source must not advertise secrets or provider transport."""
    schema = _load_schema("pipeline.json")
    defs = schema.get("$defs")
    assert isinstance(defs, dict), "pipeline.json must contain $defs section"

    source_cfg = defs.get("SourceConfig")
    assert isinstance(source_cfg, dict), "pipeline.json missing SourceConfig"

    properties = source_cfg.get("properties")
    assert isinstance(properties, dict), "SourceConfig must define properties"

    forbidden = {
        "api_key",
        "batch_size",
        "rate_limit",
        "circuit_breaker",
        "provider_config",
    }
    present = sorted(forbidden.intersection(properties))
    assert not present, (
        "pipeline.json SourceConfig still advertises forbidden entity source "
        f"fields: {present}"
    )
    for required in ("email", "fields", "api"):
        assert required in properties, (
            f"pipeline.json SourceConfig must keep entity request field {required}"
        )


def test_composite_schema_does_not_advertise_retired_column_groups_file() -> None:
    """Composite JSON schema must not expose retired merge.column_groups_file."""
    schema = _load_schema("composite.json")
    defs = schema.get("$defs")
    assert isinstance(defs, dict), "composite.json must contain $defs section"

    merge_schema = defs.get("MergeSchema")
    assert isinstance(merge_schema, dict), "composite.json missing MergeSchema"

    properties = merge_schema.get("properties")
    assert isinstance(properties, dict), "MergeSchema must define properties"

    assert "column_groups_file" not in properties, (
        "composite.json still advertises retired merge.column_groups_file"
    )


def test_configs_readme_tracks_current_legacy_status_policy() -> None:
    """Active config docs must describe the same field-status policy as schemas."""
    readme = CONFIG_README.read_text(encoding="utf-8")

    assert (
        "source `provider_config.batch_size/page_size/max_url_length/cursor_pagination`"
        in readme
    ), "configs/README.md must describe retired source provider pagination aliases"
    assert "source `batch_size`" in readme, (
        "configs/README.md must describe source.batch_size as retired"
    )
    assert "composite `merge.column_groups_file`" in readme, (
        "configs/README.md must describe composite.merge.column_groups_file as retired"
    )
    assert "composite `composite.version`" in readme, (
        "configs/README.md must describe composite.version as required"
    )
    assert "provider source `pagination.*`" in readme, (
        "configs/README.md must describe provider_config.pagination.* as the "
        "canonical source pagination contract"
    )
    assert "source `api`, `client`, and `batch`: retired migration aliases" in readme, (
        "configs/README.md must describe source.api/source.client/source.batch "
        "as retired aliases"
    )
    assert "pipeline `page_size_override`" in readme, (
        "configs/README.md must describe pipeline.page_size_override as the "
        "canonical pipeline-level pagination override"
    )
    assert "pipeline `source.api_key`" in readme, (
        "configs/README.md must describe pipeline.source.api_key as rejected"
    )
    assert "pipeline `source.batch_size`" in readme, (
        "configs/README.md must describe pipeline.source transport overrides "
        "as rejected"
    )


def test_pipeline_configuration_guide_tracks_source_pagination_policy() -> None:
    """Active pipeline guide must describe current source pagination policy."""
    guide = PIPELINE_GUIDE.read_text(encoding="utf-8")

    assert "source.provider_config.pagination.*" in guide, (
        "pipeline configuration guide must describe provider_config.pagination.* "
        "as the canonical source pagination contract"
    )
    assert "page_size_override" in guide, (
        "pipeline configuration guide must describe page_size_override as the "
        "only pipeline-level pagination override"
    )
    assert "Retired source provider pagination aliases:" in guide, (
        "pipeline configuration guide must mark source provider pagination "
        "aliases as retired"
    )
    assert "Retired source root alias:" in guide, (
        "pipeline configuration guide must mark source.batch_size as retired"
    )


def test_provider_configs_use_canonical_pagination_fields() -> None:
    """Repository provider configs should use canonical pagination.* fields only."""
    violations: list[str] = []

    for path in sorted(PROVIDERS_DIR.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            continue
        source = payload.get("source")
        if not isinstance(source, dict):
            continue
        if "batch_size" in source:
            rel = path.relative_to(PROJECT_ROOT)
            violations.append(f"{rel}: source.batch_size")
        provider_config = source.get("provider_config")
        if not isinstance(provider_config, dict):
            continue

        for key in ("batch_size", "page_size", "max_url_length", "cursor_pagination"):
            if key in provider_config:
                rel = path.relative_to(PROJECT_ROOT)
                violations.append(f"{rel}: provider_config.{key}")

    assert not violations, (
        "Provider YAML corpus must use canonical provider_config.pagination.* "
        "fields and must not keep legacy pagination aliases.\n" + "\n".join(violations)
    )


def test_provider_configs_use_declarative_environment_indirection() -> None:
    """Tracked provider YAML must avoid inline environment interpolation."""
    for path in sorted(PROVIDERS_DIR.glob("*.yaml")):
        assert "${" not in path.read_text(encoding="utf-8"), (
            f"{path}: use a documented placeholder or named *_env key"
        )

    crossref = _load_yaml_mapping(PROVIDERS_DIR / "crossref.yaml")
    openalex = _load_yaml_mapping(PROVIDERS_DIR / "openalex.yaml")
    semanticscholar = _load_yaml_mapping(PROVIDERS_DIR / "semanticscholar.yaml")
    assert "mailto" not in crossref["source"]["provider_config"]
    assert "mailto" not in openalex["source"]["provider_config"]
    assert openalex["source"]["provider_config"]["api_key_env"] == (
        "BIOETL_OPENALEX_API_KEY"
    )
    assert semanticscholar["source"]["provider_config"]["api_key_env"] == (
        "BIOETL_SEMANTICSCHOLAR_API_KEY"
    )


def test_config_version_scopes_are_explicit_semver() -> None:
    """Provider, entity, quality, and filter versions are independent SemVer scopes."""
    semver = re.compile(r"^\d+\.\d+\.\d+$")
    paths = [
        *sorted(PROVIDERS_DIR.glob("*.yaml")),
        *sorted(ENTITIES_DIR.glob("*/*.yaml")),
    ]
    for path in paths:
        payload = _load_yaml_mapping(path)
        assert semver.fullmatch(str(payload.get("version", ""))), path
        for section_name in ("quality", "filters"):
            section = payload.get(section_name)
            if isinstance(section, dict):
                assert semver.fullmatch(str(section.get("version", ""))), (
                    f"{path}: {section_name}.version must use SemVer"
                )

    chembl_activity = _load_yaml_mapping(ENTITIES_DIR / "chembl" / "activity.yaml")
    assert chembl_activity["version"] == "1.0.0"
    assert chembl_activity["quality"]["version"] == "1.1.0"


def test_composite_entity_contracts_have_complete_aligned_sections() -> None:
    """Composite entity contracts must be complete and mirror merge schemas."""
    required_sections = {"pipeline", "schema", "quality", "filters", "contracts"}
    for path in sorted((ENTITIES_DIR / "composite").glob("*.yaml")):
        payload = _load_yaml_mapping(path)
        assert required_sections <= payload.keys(), (
            f"{path}: incomplete entity contract"
        )

        runtime = _load_yaml_mapping(COMPOSITES_DIR / path.name)["composite"]
        runtime_schema = runtime.get("schema")
        runtime_merge = runtime.get("merge")
        runtime_groups = (
            runtime_schema.get("column_groups")
            if isinstance(runtime_schema, dict)
            and runtime_schema.get("column_groups") is not None
            else runtime_merge.get("column_groups")
        )
        assert payload["schema"]["column_groups"] == runtime_groups, (
            f"{path}: schema.column_groups must mirror configs/composites/{path.name}"
        )

        for layer in ("silver_filters", "gold_filters"):
            required_fields = payload["filters"][layer]["required_fields"]
            assert "entity_id" in required_fields, (
                f"{path}: filters.{layer} must require entity_id"
            )
        assert (
            payload["contracts"]["primary_key"]
            == payload["pipeline"]["business_primary_keys"]
        )


def test_config_docs_explain_runtime_values_and_version_scopes() -> None:
    """Active config docs must explain env, version, and composite contracts."""
    readme = CONFIG_README.read_text(encoding="utf-8")
    guide = PIPELINE_GUIDE.read_text(encoding="utf-8")
    for text in (readme, guide):
        assert "BIOETL_DEFAULT_EMAIL" not in text
        assert "api_key_env: BIOETL_SEMANTICSCHOLAR_API_KEY" in text
        assert "quality.version" in text
        assert "configs/entities/composite/{entity}.yaml" in text


def test_dq_schema_describes_contract_strictness_key_distinction() -> None:
    """DQ schema docs must distinguish quality-config keys from contract keys."""
    schema = _load_schema("dq.json")
    description = str(schema.get("description", ""))
    properties = schema.get("properties")
    assert isinstance(properties, dict), "dq.json must define top-level properties"
    strict_validation = properties.get("strict_validation")
    assert isinstance(strict_validation, dict), (
        "dq.json must define strict_validation property metadata"
    )

    assert "strict_dq_validation" in description, (
        "dq.json description must explain that contract YAML uses "
        "strict_dq_validation as the canonical file key"
    )
    assert "configs/contracts/*" in description
    assert "strict_dq_validation" in str(strict_validation.get("description", ""))


def test_pipeline_schema_describes_inline_dq_vs_contract_strictness() -> None:
    """pipeline.json must not present legacy contract strictness wording as canonical."""
    schema = _load_schema("pipeline.json")
    defs = schema.get("$defs")
    assert isinstance(defs, dict), "pipeline.json must contain $defs section"
    dq_schema = defs.get("DQYamlConfig")
    assert isinstance(dq_schema, dict), "pipeline.json missing DQYamlConfig definition"
    properties = dq_schema.get("properties")
    assert isinstance(properties, dict), "DQYamlConfig must define properties"
    strict_validation = properties.get("strict_validation")
    assert isinstance(strict_validation, dict), (
        "DQYamlConfig must define strict_validation property metadata"
    )
    strictness_description = str(strict_validation.get("description", ""))
    assert "strict_dq_validation" in strictness_description
    assert "inline pipeline quality config" in strictness_description
