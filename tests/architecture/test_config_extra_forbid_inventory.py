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
"""Owning tests for PSC RF-001 config ``extra`` inventory + nested-path manifest.

Issue: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12566

Covers:
* effective ``extra`` inventory (inheritance + default-ignore)
* dual registries (a) migration debt exact identity set vs (b) justified exclusions
* forbid-new permissive identities after RF-001 baseline
* full runtime-root + nested-path manifest with classification
* DQ YAML ingress = SinkDQReportConfig (no checks); projections classified
* BaseApiConfig is connection config, not adapter wire
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.architecture._config_extra_forbid_inventory import (
    BASE_API_CONFIG_IDENTITY,
    BASELINE_SHA,
    DEFAULT_JSON_OUTPUT,
    DQ_PROJECTION_IDENTITIES,
    DQ_YAML_INGRESS_IDENTITY,
    GENERATOR_COVERED_ROOTS,
    JUSTIFIED_EXCLUSIONS,
    JUSTIFIED_EXCLUSIONS_SEED,
    PIPELINE_CONTRACT_POLICY_ROOT,
    RF001_FORBID_NEW_BASELINE_IDENTITIES,
    RF003_REQUIRED_EXCLUSION_KINDS,
    RUNTIME_ONLY_ROOTS,
    WORKFLOW_CONFIG_ROOT,
    WORKFLOW_RECONCILE_FOREIGN_KEYS_IDENTITY,
    WORKFLOW_RECONCILE_ROWS_IDENTITY,
    WORKFLOW_TRANSFORM_CONFIG_PATH,
    build_payload,
    render_payload,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "reports" / "quality" / "config-extra-forbid-inventory.json"


@pytest.mark.generated_artifact
def test_config_extra_forbid_inventory_artifact_matches_generator() -> None:
    """Committed inventory must match the live schemas scan."""
    expected = render_payload(build_payload())
    assert INVENTORY_PATH == DEFAULT_JSON_OUTPUT
    actual = INVENTORY_PATH.read_text(encoding="utf-8")
    assert actual == expected


@pytest.mark.generated_artifact
def test_config_extra_forbid_inventory_counts_match_effective_policy() -> None:
    """Counts track live effective policy; RF-001 baseline preserved via SHA + ceiling.

    RF-001 land counts (67/11/27 local; effective 69/36) are historical provenance
    in the plan / RF-001 notes — not a forever soft-assert. After RF-002 forbid
    migration, live inventory must report debt-cleared effective policy.
    """
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    live = build_payload()
    counts = payload["counts"]
    assert counts == live["counts"]
    assert counts["basemodel_total"] == 105
    # RF-002: all previous effective-ignore identities migrated to forbid.
    assert counts["local_ignore"] == 0
    assert counts["among_none_inherited_ignore"] == 0
    assert counts["among_none_default_ignore"] == 0
    assert counts["effective_ignore"] == 0
    assert counts["effective_forbid"] == 105
    assert counts["local_forbid"] + counts["local_none"] == 105
    assert counts["among_none_inherited_forbid"] == counts["local_none"]
    # Provenance: RF-001 baseline SHA + forbid-new ceiling remain pinned.
    assert payload["baseline_sha"] == BASELINE_SHA
    assert len(RF001_FORBID_NEW_BASELINE_IDENTITIES) == 36


@pytest.mark.generated_artifact
def test_migration_debt_is_exact_identity_set_of_effective_ignore() -> None:
    """Registry (a): exact sorted identity set — no countdown-only soft ratchet.

    RF-002 completion criterion: debt (a) == [] after real forbid migration.
    """
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    live = build_payload()
    debt = payload["migration_debt_identities"]
    assert debt == live["migration_debt_identities"]
    assert debt == sorted(debt)
    assert len(debt) == payload["counts"]["effective_ignore"]
    live_ignore = sorted(
        row["identity"] for row in live["models"] if row["effective_extra"] == "ignore"
    )
    assert debt == live_ignore
    assert debt == []
    assert payload["counts"]["effective_ignore"] == 0


@pytest.mark.generated_artifact
def test_justified_exclusions_registry_is_separate_from_migration_debt() -> None:
    """Registry (b) finalized set must not overlap migration debt identities."""
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    debt = set(payload["migration_debt_identities"])
    exclusions = payload["justified_exclusions"]
    exclusion_ids = [item["identity"] for item in exclusions]
    assert exclusion_ids == sorted(exclusion_ids)
    assert set(exclusion_ids).isdisjoint(debt)
    # JUSTIFIED_EXCLUSIONS_SEED is a back-compat alias of JUSTIFIED_EXCLUSIONS.
    assert JUSTIFIED_EXCLUSIONS_SEED is JUSTIFIED_EXCLUSIONS
    finalized_ids = {item["identity"] for item in JUSTIFIED_EXCLUSIONS}
    assert set(exclusion_ids) == finalized_ids
    kinds = {item["kind"] for item in exclusions}
    assert RF003_REQUIRED_EXCLUSION_KINDS <= kinds
    assert {
        "env-settings",
        "open-dict-typealias",
        "adapter-wire-models",
        "open-dict-field",
    } <= kinds


@pytest.mark.generated_artifact
def test_forbid_new_permissive_identities_after_baseline() -> None:
    """Forbid-new uses a frozen identity ceiling, not the regenerable debt list.

    Codex P2: comparing live_ignore to regenerable ``migration_debt_identities``
    is tautological after inventory refresh and allows ignore↔forbid swaps.
    Authority is ``RF001_FORBID_NEW_BASELINE_IDENTITIES`` in the helper module.
    """
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    frozen = RF001_FORBID_NEW_BASELINE_IDENTITIES
    # Artifact may document the ceiling, but regeneration must echo the constant
    # — it must not become an independent mutable baseline.
    assert payload["forbid_new_baseline_identities"] == sorted(frozen)
    assert set(payload["forbid_new_baseline_identities"]) == frozen

    live = build_payload()
    live_ignore = {
        row["identity"] for row in live["models"] if row["effective_extra"] == "ignore"
    }
    new_permissive = sorted(live_ignore - frozen)
    assert new_permissive == [], (
        "Forbid-new permissive identities after RF-001 baseline; "
        f"unexpected effective-ignore models: {new_permissive}"
    )
    # Current regenerable debt may shrink under the ceiling (RF-002), but must
    # never exceed it and must match the live scan.
    debt = set(payload["migration_debt_identities"])
    assert debt == live_ignore
    assert debt <= frozen
    assert len(frozen) == 36


@pytest.mark.generated_artifact
def test_full_manifest_covers_runtime_roots_and_nested_paths() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    roots = payload["runtime_roots"]
    paths = payload["nested_paths"]
    root_ids = {row["identity"] for row in roots}
    assert set(GENERATOR_COVERED_ROOTS) <= root_ids
    assert set(RUNTIME_ONLY_ROOTS) <= root_ids
    assert paths, "nested path manifest must be non-empty"
    # Every nested path row must carry a classification from the RF-001 set.
    allowed = {
        "forbid",
        "generator-covered",
        "migration-debt",
        "runtime-only",
        "justified-exclusion",
        "unclassified-permissive",
    }
    for row in paths:
        assert row["classification"] in allowed, row
        assert row["path"]
        assert row["identity"]
        assert row["root"] in root_ids
    for row in roots:
        if row["identity"] in GENERATOR_COVERED_ROOTS:
            assert row["coverage"] == "generator-covered"
            assert row["schema_artifact"] == GENERATOR_COVERED_ROOTS[row["identity"]]
        if row["identity"] in RUNTIME_ONLY_ROOTS:
            assert row["coverage"] == "runtime-only"
            assert row["schema_artifact"] is None


@pytest.mark.generated_artifact
def test_dq_ingress_vs_projection_classification() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    models = {row["identity"]: row for row in payload["models"]}
    ingress = models[DQ_YAML_INGRESS_IDENTITY]
    assert ingress["role"] == "dq-yaml-ingress"
    # RF-002: ingress migrated to forbid; still no checks field (PSC-5).
    assert ingress["effective_extra"] == "forbid"
    assert DQ_YAML_INGRESS_IDENTITY not in payload["migration_debt_identities"]

    # Ingress must appear under PipelineYamlConfig.sink.dq_report path.
    ingress_paths = [
        row
        for row in payload["nested_paths"]
        if row["identity"] == DQ_YAML_INGRESS_IDENTITY
    ]
    assert any(
        row["path"] == "sink.dq_report" and "PipelineYamlConfig" in row["root"]
        for row in ingress_paths
    ), ingress_paths

    for identity in sorted(DQ_PROJECTION_IDENTITIES):
        row = models[identity]
        assert row["role"] == "dq-layer-projection"
        assert row["effective_extra"] == "forbid"
        assert identity not in payload["migration_debt_identities"]
        assert "checks" in str(row.get("notes", "")) or identity.endswith("SinkConfig")

    # SinkDQReportConfig must NOT credit a checks field (PSC-5).
    from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
        SinkDQReportConfig,
    )

    assert "checks" not in SinkDQReportConfig.model_fields
    assert set(SinkDQReportConfig.model_fields) == {
        "enabled",
        "output_path",
        "format",
    }


@pytest.mark.generated_artifact
def test_base_api_config_not_classified_as_wire_dto() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    models = {row["identity"]: row for row in payload["models"]}
    api = models[BASE_API_CONFIG_IDENTITY]
    assert api["role"] == "api-connection-config"
    assert api.get("not_wire_dto") is True
    # RF-002: migrated to forbid (connection config), not moved to wire exclusions.
    assert api["effective_extra"] == "forbid"
    assert BASE_API_CONFIG_IDENTITY not in payload["migration_debt_identities"]
    # Must not appear in justified adapter-wire exclusion as a class identity.
    exclusion_ids = {item["identity"] for item in payload["justified_exclusions"]}
    assert BASE_API_CONFIG_IDENTITY not in exclusion_ids
    wire = next(
        item
        for item in payload["justified_exclusions"]
        if item["kind"] == "adapter-wire-models"
    )
    assert "BaseApiConfig" in wire["rationale"] or "Do not confuse" in wire["rationale"]


@pytest.mark.generated_artifact
def test_manifest_includes_workflow_and_contract_policy_roots() -> None:
    """load_workflow_config / load_pipeline_contract_policy roots must be reachable."""
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    roots = {row["identity"]: row for row in payload["runtime_roots"]}
    models = {row["identity"]: row for row in payload["models"]}

    assert WORKFLOW_CONFIG_ROOT in roots
    assert PIPELINE_CONTRACT_POLICY_ROOT in roots
    assert WORKFLOW_CONFIG_ROOT in RUNTIME_ONLY_ROOTS
    assert PIPELINE_CONTRACT_POLICY_ROOT in RUNTIME_ONLY_ROOTS

    workflow_root = roots[WORKFLOW_CONFIG_ROOT]
    assert workflow_root["coverage"] == "runtime-only"
    assert workflow_root["schema_artifact"] is None
    assert workflow_root["role"] == "workflow-config-root"
    # Already local forbid — classification is forbid; coverage remains runtime-only
    # (absent from generate-pipeline SCHEMAS).
    assert workflow_root["effective_extra"] == "forbid"
    assert workflow_root["classification"] == "forbid"

    contract_root = roots[PIPELINE_CONTRACT_POLICY_ROOT]
    assert contract_root["coverage"] == "runtime-only"
    assert contract_root["schema_artifact"] is None
    assert contract_root["role"] == "pipeline-contract-policy-root"
    assert contract_root["effective_extra"] == "forbid"
    assert contract_root["classification"] == "forbid"

    assert models[WORKFLOW_CONFIG_ROOT]["reachable_from_runtime_roots"] is True
    assert models[PIPELINE_CONTRACT_POLICY_ROOT]["reachable_from_runtime_roots"] is True

    workflow_paths = {
        row["path"]
        for row in payload["nested_paths"]
        if row["root"] == WORKFLOW_CONFIG_ROOT
    }
    assert "workflow.defaults" in workflow_paths
    assert "workflow.steps" in workflow_paths

    contract_paths = {
        row["path"]
        for row in payload["nested_paths"]
        if row["root"] == PIPELINE_CONTRACT_POLICY_ROOT
    }
    assert "$" in contract_paths
    assert "rollout" in contract_paths

    # Nested workflow / contract models used by those loaders must be reachable.
    for identity_suffix in (
        "WorkflowConfigSchema",
        "WorkflowDefaultsSchema",
        "PipelineContractRollout",
    ):
        matches = [
            row
            for row in payload["models"]
            if row["identity"].endswith(f".{identity_suffix}")
        ]
        assert matches, identity_suffix
        assert all(row["reachable_from_runtime_roots"] is True for row in matches), (
            matches
        )

    # JsonDict-backed transform configs validated dynamically by transform_name.
    for identity in (
        WORKFLOW_RECONCILE_ROWS_IDENTITY,
        WORKFLOW_RECONCILE_FOREIGN_KEYS_IDENTITY,
    ):
        assert models[identity]["reachable_from_runtime_roots"] is True, identity
        assert models[identity]["role"] == "workflow-transform-config"
        edge_rows = [
            row
            for row in payload["nested_paths"]
            if row["identity"] == identity and row["root"] == WORKFLOW_CONFIG_ROOT
        ]
        assert edge_rows, identity
        assert any(
            row["path"] == WORKFLOW_TRANSFORM_CONFIG_PATH for row in edge_rows
        ), edge_rows
        assert all(
            row.get("edge_kind") == "explicit-json-dict-config" for row in edge_rows
        ), edge_rows
