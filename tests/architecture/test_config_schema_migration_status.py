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
from pathlib import Path
from typing import Any

import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = PROJECT_ROOT / "configs" / "_schema"
CONFIG_README = PROJECT_ROOT / "configs" / "README.md"
PIPELINE_GUIDE = PROJECT_ROOT / "docs" / "03-guides" / "pipeline-configuration.md"
PROVIDERS_DIR = PROJECT_ROOT / "configs" / "providers"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


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
    """Pipeline JSON schema must not expose direct source pagination override keys."""
    schema = _load_schema("pipeline.json")
    defs = schema.get("$defs")
    assert isinstance(defs, dict), "pipeline.json must contain $defs section"

    provider_source = defs.get("ProviderSourceConfig")
    assert isinstance(provider_source, dict), (
        "pipeline.json missing ProviderSourceConfig definition"
    )

    properties = provider_source.get("properties")
    assert isinstance(properties, dict), (
        "ProviderSourceConfig must define properties in pipeline.json"
    )

    forbidden = {"batch_size", "page_size", "max_url_length"}
    present = sorted(forbidden.intersection(properties))
    assert not present, (
        "pipeline.json still advertises direct source pagination override keys "
        f"inside ProviderSourceConfig: {present}"
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
