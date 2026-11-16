"""Resolve maintenance deployment through the same settings and YAML as writers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import cast

import yaml

from bioetl.composition.factories.storage.target_paths import resolve_target_table_paths
from bioetl.composition.target_classification import load_target_runtime_profile
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_uncached,
)
from bioetl.infrastructure.config.settings_api import Settings, get_settings
from bioetl.infrastructure.config.target_classification_profile import (
    resolve_target_classification_profile,
)
from bioetl.infrastructure.schemas.target_classification_config import (
    TargetClassificationYamlConfig,
)
from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationPaths,
)
from bioetl.infrastructure.storage.target_deployment_binding import (
    TargetDeploymentBinding,
)
from iuphar_target_class.stage0.io import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)


def _entity_document(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_bytes())
    if not isinstance(value, dict) or not isinstance(value.get("pipeline"), dict):
        raise ValueError("migration configuration must be a complete entity YAML")
    return cast("dict[str, object]", value)


def _without_classification(document: dict[str, object]) -> dict[str, object]:
    value = deepcopy(document)
    pipeline = cast("dict[str, object]", value["pipeline"])
    pipeline.pop("target_classification", None)
    return value


def bind_target_deployment(
    paths: TargetMigrationPaths,
    *,
    settings: Settings | None = None,
    configs_root: Path | None = None,
) -> TargetDeploymentBinding:
    """Permit a classification-only change at the actual canonical entity path.

    Build routing is supplied separately as candidate destinations. The file
    promoted into the canonical configuration must retain the original sinks,
    filters and business rules. All implicit defaults are resolved by the real
    public loader; no temporary checkout or shadow filesystem is required.
    """
    checked = paths.checked()
    root = resolve_configs_root(configs_root).resolve()
    canonical = (root / "entities/chembl/target.yaml").resolve()
    if checked["config"] != canonical or paths.workspace.resolve() != root.parent:
        raise ValueError("migration workspace/config must match the active config root")
    original = _entity_document(canonical)
    deployment = _entity_document(checked["candidate_config"])
    if _without_classification(original) != _without_classification(deployment):
        raise ValueError("deployment YAML may change only target_classification")
    pipeline = cast("dict[str, object]", deployment["pipeline"])
    classification = TargetClassificationYamlConfig.model_validate(
        pipeline.get("target_classification")
    )
    if classification.mode != "enrich":
        raise ValueError("deployment configuration must select enrich")
    baseline = load_pipeline_config_uncached("chembl_target", configs_root=root)
    future = baseline.model_copy(update={"target_classification": classification})
    future = resolve_target_classification_profile(future).resolved_yaml_config
    profile = load_target_runtime_profile(future)
    if profile is None:
        raise ValueError("deployment has no admitted profile")
    active_settings = settings or get_settings()
    silver, gold = resolve_target_table_paths(active_settings, future)
    if (silver.resolve(), gold.resolve()) != (checked["silver"], checked["gold"]):
        raise ValueError("deployment resolves different physical target destinations")
    settings_digest = sha256_bytes(
        canonical_json_bytes(
            {
                "data_dir": str(active_settings.data_dir.resolve()),
                "configs_root": str(root),
                "silver": str(silver.resolve()),
                "gold": str(gold.resolve()),
            }
        )
    )
    return TargetDeploymentBinding(
        str(canonical),
        sha256_file(canonical),
        sha256_file(checked["candidate_config"]),
        str(silver.resolve()),
        str(gold.resolve()),
        profile.profile_sha256,
        settings_digest,
    )


__all__ = ["bind_target_deployment"]
