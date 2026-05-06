"""Registry and DQ coverage for active standard pipeline contract surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.dq_contract_config_loader import (
    DQContractConfigLoader,
)
from bioetl.infrastructure.control_plane import FileContractRegistryStore

_CONFIGS_ROOT = Path("configs")
_ENTITY_CONFIGS_ROOT = _CONFIGS_ROOT / "entities"
_REGISTRY_PATH = _CONFIGS_ROOT / "base" / "contract_registry.yaml"
_FIXTURE_GAPS_PATH = _CONFIGS_ROOT / "base" / "bronze_fixture_gaps.yaml"
_FIXTURE_MANIFEST_PATH = _CONFIGS_ROOT / "base" / "bronze_fixture_manifest.yaml"
_GOLD_CONTRACTS_ROOT = Path("docs/04-reference/contracts/gold")
_STANDARD_CONTRACT_PROVIDERS = {
    "chembl",
    "crossref",
    "openalex",
    "pubchem",
    "pubmed",
    "semanticscholar",
    "uniprot",
}
_SPECIALIZED_CHEMBL_FIXTURE_CONTRACT_REFS = {
    "chembl.assay_parameters",
    "chembl.publication_similarity",
    "chembl.publication_term",
    "chembl.subcellular_fraction",
}
_ALLOWED_ACTIVE_REGISTRY_REFS_WITHOUT_ENTITY_CONFIG: frozenset[str] = frozenset()


def _active_standard_contract_refs() -> dict[str, str]:
    """Return pipeline_name -> contract_ref for active non-composite surfaces."""
    refs: dict[str, str] = {}
    for config_path in sorted(_ENTITY_CONFIGS_ROOT.glob("*/*.yaml")):
        provider = config_path.parent.name
        if provider not in _STANDARD_CONTRACT_PROVIDERS:
            continue
        if not _gold_runtime_enabled(config_path):
            continue
        entity = config_path.stem
        pipeline_name = f"{provider}_{entity}"
        refs[pipeline_name] = f"{provider}.{entity}"
    return refs


def _gold_runtime_enabled(config_path: Path) -> bool:
    """Return True when an entity config publishes a live Gold runtime surface."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    pipeline = config.get("pipeline")
    if not isinstance(pipeline, dict):
        return True
    sink = pipeline.get("sink")
    if not isinstance(sink, dict):
        return True
    gold = sink.get("gold")
    if not isinstance(gold, dict):
        return True
    enabled = gold.get("enabled")
    return True if enabled is None else bool(enabled)


def _fixture_gap_payload() -> dict[str, object]:
    payload = yaml.safe_load(_FIXTURE_GAPS_PATH.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    return payload


def _fixture_manifest_payload() -> dict[str, object]:
    payload = yaml.safe_load(_FIXTURE_MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    return payload


@pytest.mark.integration
def test_contract_registry_covers_active_standard_provider_surfaces() -> None:
    """Every active standard provider/entity config must be registry-governed."""
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()
    expected_refs = set(_active_standard_contract_refs().values())

    assert expected_refs <= set(registry.entries), (
        "Contract registry missing active provider surfaces: "
        f"{sorted(expected_refs - set(registry.entries))}"
    )


@pytest.mark.integration
def test_contract_registry_dq_identity_metadata_is_entry_aligned() -> None:
    """Registry DQ identity anchors must match entry-level metadata."""
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()

    mismatches = [
        contract_ref
        for contract_ref, entry in sorted(registry.entries.items())
        if entry.identity.dq_policy_ref != entry.dq_policy_ref
        or entry.identity.rule_bundle_version != entry.rule_bundle_version
    ]

    assert mismatches == []


@pytest.mark.integration
def test_active_contract_registry_surfaces_have_active_entity_config_or_alias_governance() -> (
    None
):
    """Every active standard registry ref must map back to config or alias governance."""
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()
    expected_refs = set(_active_standard_contract_refs().values())
    active_registry_refs = {
        ref
        for ref, entry in registry.entries.items()
        if ref.split(".", maxsplit=1)[0] in _STANDARD_CONTRACT_PROVIDERS
        and entry.status.value == "active"
    }
    uncovered = active_registry_refs - expected_refs
    allowed = _ALLOWED_ACTIVE_REGISTRY_REFS_WITHOUT_ENTITY_CONFIG

    assert uncovered <= allowed, (
        "Active registry refs must have an active entity config or explicit alias "
        "governance: "
        f"{sorted(uncovered - allowed)}"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("pipeline_name", "contract_ref"),
    sorted(_active_standard_contract_refs().items()),
)
def test_active_standard_provider_surface_has_dq_config_and_published_artifact(
    pipeline_name: str,
    contract_ref: str,
) -> None:
    """Active provider surfaces must resolve DQ config and published Gold artifact."""
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()
    entry = registry.entries[contract_ref]
    expected_artifact = (
        f"../../docs/04-reference/contracts/gold/{pipeline_name}_v1.0.json"
    )

    dq_config = DQContractConfigLoader(_CONFIGS_ROOT).load_dq_config_for_pipeline(
        pipeline_name
    )

    assert dq_config.contract_ref == contract_ref
    assert dq_config.contract_version == entry.identity.contract_version
    assert dq_config.rule_bundle_version == entry.identity.rule_bundle_version
    assert expected_artifact in entry.published_artifacts
    assert (_GOLD_CONTRACTS_ROOT / f"{pipeline_name}_v1.0.json").exists()


@pytest.mark.integration
def test_gold_disabled_standard_surface_can_stay_registry_published_but_not_active() -> (
    None
):
    """Gold-disabled standard surfaces may keep published artifacts without active status."""
    activity_config = _ENTITY_CONFIGS_ROOT / "chembl" / "activity.yaml"
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()

    assert _gold_runtime_enabled(activity_config) is False
    assert registry.entries["chembl.activity"].status.value == "deprecated"


@pytest.mark.integration
def test_specialized_chembl_fixture_surfaces_are_active_contracts_when_gold_runs() -> (
    None
):
    """Specialized ChEMBL Gold surfaces must stay active while entity configs publish Gold."""
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()

    statuses = {
        contract_ref: registry.entries[contract_ref].status.value
        for contract_ref in sorted(_SPECIALIZED_CHEMBL_FIXTURE_CONTRACT_REFS)
    }

    assert statuses == {
        "chembl.assay_parameters": "active",
        "chembl.publication_similarity": "active",
        "chembl.publication_term": "active",
        "chembl.subcellular_fraction": "active",
    }


@pytest.mark.integration
def test_crossref_works_is_compatibility_only_not_active_runtime_surface() -> None:
    """Legacy Crossref works ref must not compete with crossref.publication."""
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()

    assert registry.entries["crossref.publication"].status.value == "active"
    assert registry.entries["crossref.works"].status.value == "deprecated"


@pytest.mark.integration
def test_specialized_chembl_fixture_surfaces_have_tracked_manifest_evidence() -> None:
    """Specialized ChEMBL surfaces must resolve to tracked manifest evidence."""
    payload = _fixture_manifest_payload()
    fixtures = payload.get("fixtures", {})
    assert isinstance(fixtures, dict)

    expected = {
        "chembl/assay_parameters": "deterministic_adapter_projection",
        "chembl/publication_similarity": "provider_contract_alignment",
        "chembl/publication_term": "recorded_provider_or_deterministic_derived_source",
        "chembl/subcellular_fraction": "controlled_extraction_run",
    }

    for fixture_name, resolution_kind in expected.items():
        entry = fixtures.get(fixture_name)
        assert isinstance(entry, dict), (
            f"missing fixture manifest entry: {fixture_name}"
        )
        assert entry.get("fixture_kind") == "tracked_ci_sample"
        assert entry.get("validation_status") == "valid"
        assert entry.get("resolution_kind") == resolution_kind


@pytest.mark.integration
def test_bronze_fixture_gap_registry_is_empty_after_fixture_closeout() -> None:
    """Tracked fixture manifest should eliminate the residual Bronze gap registry."""
    payload = _fixture_gap_payload()
    gaps = payload.get("gaps", {})
    assert isinstance(gaps, dict)
    assert gaps == {}
