"""Runtime-management bundle for composite runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import (
        CompositeCheckpointService,
        FSMStateHelperService,
    )
    from bioetl.application.services.quality.dq_report_service import DQReportService
    from bioetl.domain.ports import QuarantinePort


@dataclass(slots=True)
class RuntimeManagementServicesBundle:
    """Checkpoint, FSM, DQ, and quarantine services for runtime orchestration."""

    checkpoint_manager: CompositeCheckpointService
    dq_report_service: DQReportService
    fsm_state_helper: FSMStateHelperService
    quarantine_port: QuarantinePort | None


__all__ = ["RuntimeManagementServicesBundle"]

from copy import deepcopy
from pathlib import Path
from typing import cast

import yaml

from bioetl.composition.factories.dq.composite_validation import resolve_target_table_paths
from bioetl.composition.bootstrap.runtime.publication_vocab_init import load_target_runtime_profile
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
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationPaths,
)
from bioetl.infrastructure.storage.target_deployment_binding import (
    TargetDeploymentBinding,
    validate_rehearsal_paths,
)
from iuphar_target_class.stage0.io import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

EntityDocument = dict[str, object]
_CANONICAL_TARGET_ENTITY = "entities/chembl/target.yaml"


def _entity_document(path: Path) -> EntityDocument:
    value = yaml.safe_load(path.read_bytes())
    if not isinstance(value, dict) or not isinstance(value.get("pipeline"), dict):
        raise ValueError("migration configuration must be a complete entity YAML")
    return cast(EntityDocument, value)


def _without_classification(document: EntityDocument) -> EntityDocument:
    value = deepcopy(document)
    pipeline = cast(EntityDocument, value["pipeline"])
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
    canonical = (root / _CANONICAL_TARGET_ENTITY).resolve()
    if checked["config"] != canonical or paths.workspace.resolve() != root.parent:
        raise ValueError("migration workspace/config must match the active config root")
    original = _entity_document(canonical)
    deployment = _entity_document(checked["candidate_config"])
    if _without_classification(original) != _without_classification(deployment):
        raise ValueError("deployment YAML may change only target_classification")
    pipeline = cast(EntityDocument, deployment["pipeline"])
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


def _rehearsal_locations(
    paths: TargetMigrationPaths,
    rehearsal_root: Path,
    configs_root: Path,
    settings: Settings,
    active_configs_root: Path | None,
) -> tuple[dict[str, Path], Path, Path]:
    checked = paths.checked()
    active = resolve_configs_root(active_configs_root).resolve()
    if paths.workspace.resolve() != active.parent:
        raise ValueError(
            "rehearsal workspace must match the active repository/config root"
        )
    root = validate_rehearsal_paths(
        checked, workspace=paths.workspace, rehearsal_root=rehearsal_root
    )
    copied = resolve_configs_root(configs_root).resolve()
    if not copied.is_relative_to(root) or checked["config"] != (
        copied / _CANONICAL_TARGET_ENTITY
    ):
        raise ValueError("rehearsal must load its copied configs tree")
    canonical = active / _CANONICAL_TARGET_ENTITY
    if sha256_file(canonical) != sha256_file(checked["config"]):
        raise ValueError(
            "rehearsal old configuration must equal the active canonical bytes"
        )
    if not settings.test_mode or not settings.data_dir.resolve().is_relative_to(root):
        raise ValueError(
            "rehearsal requires explicit isolated test_mode storage settings"
        )
    return checked, copied, active


def _rehearsal_future(
    checked: dict[str, Path], configs_root: Path
) -> PipelineYamlConfig:
    original = _entity_document(checked["config"])
    deployment = _entity_document(checked["candidate_config"])
    if _without_classification(original) != _without_classification(deployment):
        raise ValueError("deployment YAML may change only target_classification")
    pipeline = cast(EntityDocument, deployment["pipeline"])
    classification = TargetClassificationYamlConfig.model_validate(
        pipeline.get("target_classification")
    )
    if classification.mode != "enrich":
        raise ValueError("deployment configuration must select enrich")
    baseline = load_pipeline_config_uncached("chembl_target", configs_root=configs_root)
    future = baseline.model_copy(update={"target_classification": classification})
    return resolve_target_classification_profile(future).resolved_yaml_config


def _protect_active_resources(
    checked: dict[str, Path], active_configs_root: Path
) -> None:
    settings = get_settings()
    target = load_pipeline_config_uncached(
        "chembl_target", configs_root=active_configs_root
    )
    assay = load_pipeline_config_uncached(
        "chembl_assay", configs_root=active_configs_root
    )
    protected = tuple(
        path.resolve()
        for path in (
            active_configs_root / _CANONICAL_TARGET_ENTITY,
            *resolve_target_table_paths(settings, target),
            resolve_target_table_paths(settings, assay)[1],
        )
    )
    for path in checked.values():
        if any(
            path == item or path.is_relative_to(item) or item.is_relative_to(path)
            for item in protected
        ):
            raise ValueError(
                "rehearsal resources overlap active canonical data/configuration"
            )


def bind_target_rehearsal(
    paths: TargetMigrationPaths,
    *,
    rehearsal_root: Path,
    configs_root: Path,
    settings: Settings,
    active_configs_root: Path | None = None,
) -> TargetDeploymentBinding:
    """Bind an isolated physical rehearsal through the real loader and admission.

    The approved repository remains the read-only dependency scope, allowing
    exact pinned absolute receipt URIs. Every resource moved or written by
    migration is fenced inside the explicit copy occurrence. The existing
    repository advisory lock is shared with production maintenance.
    """
    checked, copied, active = _rehearsal_locations(
        paths, rehearsal_root, configs_root, settings, active_configs_root
    )
    _protect_active_resources(checked, active)
    future = _rehearsal_future(checked, copied)
    profile = load_target_runtime_profile(future)
    if profile is None:
        raise ValueError("rehearsal has no admitted profile")
    silver, gold = resolve_target_table_paths(settings, future)
    if (silver.resolve(), gold.resolve()) != (checked["silver"], checked["gold"]):
        raise ValueError("rehearsal resolves different physical target destinations")
    settings_digest = sha256_bytes(
        canonical_json_bytes(
            {
                "data_dir": str(settings.data_dir.resolve()),
                "configs_root": str(copied),
                "silver": str(silver.resolve()),
                "gold": str(gold.resolve()),
                "role": "rehearsal",
                "rehearsal_root": str(rehearsal_root.resolve()),
                "approved_workspace": str(paths.workspace.resolve()),
            }
        )
    )
    return TargetDeploymentBinding(
        str(checked["config"]),
        sha256_file(checked["config"]),
        sha256_file(checked["candidate_config"]),
        str(silver.resolve()),
        str(gold.resolve()),
        profile.profile_sha256,
        settings_digest,
        role="rehearsal",
        rehearsal_root=str(rehearsal_root.resolve()),
        approved_workspace=str(paths.workspace.resolve()),
    )


__all__ = ["bind_target_deployment", "bind_target_rehearsal"]
