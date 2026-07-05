"""Architecture test: explicit Gold SCD2 policy for SCD2-candidate configs.

REQ-ARCH-052: SCD2-candidate entity configs MUST explicitly declare
`pipeline.sink.gold.mode: scd2` and a complete canonical `scd_config`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PUBLICATION_CONFIGS = (
    "configs/entities/chembl/publication.yaml",
    "configs/entities/pubmed/publication.yaml",
    "configs/entities/crossref/publication.yaml",
    "configs/entities/openalex/publication.yaml",
    "configs/entities/semanticscholar/publication.yaml",
)

REFERENCE_DICTIONARY_CONFIGS = (
    "configs/entities/chembl/assay.yaml",
    "configs/entities/chembl/assay_parameters.yaml",
    "configs/entities/chembl/cell_line.yaml",
    "configs/entities/chembl/tissue.yaml",
    "configs/entities/chembl/protein_class.yaml",
    "configs/entities/chembl/subcellular_fraction.yaml",
)

SLOWLY_EVOLVING_CONFIGS = (
    "configs/entities/chembl/target.yaml",
    "configs/entities/chembl/target_component.yaml",
    "configs/entities/chembl/molecule.yaml",
    "configs/entities/chembl/compound_record.yaml",
    "configs/entities/uniprot/protein.yaml",
    "configs/entities/uniprot/idmapping.yaml",
    "configs/entities/pubchem/compound.yaml",
)

SCD2_CANDIDATE_CONFIGS = (
    *PUBLICATION_CONFIGS,
    *REFERENCE_DICTIONARY_CONFIGS,
    *SLOWLY_EVOLVING_CONFIGS,
)

REQUIRED_SCD_CONFIG_KEYS = frozenset(
    {"valid_from_col", "valid_to_col", "current_flag_col", "version_col"}
)
LEGACY_SCD_CONFIG_ALIAS_KEYS = frozenset(
    {"valid_from", "valid_to", "is_current", "version"}
)


def _load_yaml(path: str) -> dict[str, object]:
    config_path = PROJECT_ROOT / path
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        pytest.fail(f"{path} must load as a mapping")
    return data


def _load_pipeline_gold_config(path: str) -> dict[str, Any]:
    config = _load_yaml(path)
    provider = str(config.get("provider", "")).strip()
    entity = str(config.get("entity", "")).strip()
    if not provider or not entity:
        pytest.fail(f"{path} must declare provider/entity for effective config loading")

    pipeline_cfg = load_pipeline_config_from_root(
        f"{provider}_{entity}",
        configs_root=PROJECT_ROOT / "configs",
    ).model_dump(mode="python")
    sink_cfg = pipeline_cfg.get("sink")
    if not isinstance(sink_cfg, dict):
        pytest.fail(f"{path} must contain pipeline.sink")

    gold_cfg = sink_cfg.get("gold")
    if not isinstance(gold_cfg, dict):
        pytest.fail(f"{path} must contain pipeline.sink.gold")

    return gold_cfg


class TestExplicitGoldScd2Policy:
    """ADR-018 / RULES gate for explicit Gold SCD2 policy."""

    @pytest.mark.parametrize("config_path", SCD2_CANDIDATE_CONFIGS)
    def test_scd2_candidates_have_explicit_gold_scd2_mode(
        self, config_path: str
    ) -> None:
        gold_cfg = _load_pipeline_gold_config(config_path)
        assert gold_cfg.get("mode") == "scd2", (
            f"{config_path} MUST declare pipeline.sink.gold.mode: scd2 "
            "for SCD2-candidate entities."
        )

    @pytest.mark.parametrize("config_path", SCD2_CANDIDATE_CONFIGS)
    def test_scd2_candidates_define_complete_canonical_scd_config(
        self, config_path: str
    ) -> None:
        gold_cfg = _load_pipeline_gold_config(config_path)
        scd_config = gold_cfg.get("scd_config")
        assert isinstance(scd_config, dict), (
            f"{config_path} MUST define pipeline.sink.gold.scd_config."
        )

        missing_keys = REQUIRED_SCD_CONFIG_KEYS.difference(scd_config)
        assert not missing_keys, (
            f"{config_path} is missing required scd_config keys: {sorted(missing_keys)}"
        )

        legacy_keys = LEGACY_SCD_CONFIG_ALIAS_KEYS.intersection(scd_config)
        assert not legacy_keys, (
            f"{config_path} MUST use canonical scd_config keys only; "
            f"found legacy aliases: {sorted(legacy_keys)}"
        )

    def test_all_publication_configs_are_covered(self) -> None:
        configs_dir = PROJECT_ROOT / "configs" / "entities"
        found_publication_configs: list[str] = []
        for path in configs_dir.glob("**/publication.yaml"):
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(payload, dict):
                continue
            # SCD2 policy applies only to standalone pipeline entity configs.
            pipeline_cfg = payload.get("pipeline")
            if not isinstance(pipeline_cfg, dict):
                continue
            if payload.get("provider") == "composite":
                continue
            if pipeline_cfg.get("provider") == "composite":
                continue
            found_publication_configs.append(
                str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            )
        assert sorted(found_publication_configs) == sorted(PUBLICATION_CONFIGS), (
            "Publication SCD2 candidate list drifted. Update PUBLICATION_CONFIGS in "
            "tests/architecture/test_explicit_gold_scd2_policy.py."
        )
