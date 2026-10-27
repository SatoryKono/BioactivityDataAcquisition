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
    JUSTIFIED_EXCLUSIONS_SEED,
    RUNTIME_ONLY_ROOTS,
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
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    counts = payload["counts"]
    assert counts["basemodel_total"] == 105
    assert counts["local_forbid"] == 67
    assert counts["local_ignore"] == 11
    assert counts["local_none"] == 27
    assert counts["among_none_inherited_forbid"] == 2
    assert counts["among_none_inherited_ignore"] == 12
    assert counts["among_none_default_ignore"] == 13
    assert counts["effective_forbid"] == 69
    assert counts["effective_ignore"] == 36
    assert payload["baseline_sha"] == BASELINE_SHA


@pytest.mark.generated_artifact
def test_migration_debt_is_exact_identity_set_of_effective_ignore() -> None:
    """Registry (a): exact sorted identity set — no countdown-only soft ratchet."""
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    live = build_payload()
    debt = payload["migration_debt_identities"]
    assert debt == live["migration_debt_identities"]
    assert debt == sorted(debt)
    assert len(debt) == payload["counts"]["effective_ignore"]
    live_ignore = sorted(
        row["identity"]
        for row in live["models"]
        if row["effective_extra"] == "ignore"
    )
    assert debt == live_ignore


@pytest.mark.generated_artifact
def test_justified_exclusions_registry_is_separate_from_migration_debt() -> None:
    """Registry (b) seed must not overlap migration debt identities."""
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    debt = set(payload["migration_debt_identities"])
    exclusions = payload["justified_exclusions"]
    exclusion_ids = [item["identity"] for item in exclusions]
    assert exclusion_ids == sorted(exclusion_ids)
    assert set(exclusion_ids).isdisjoint(debt)
    seed_ids = {item["identity"] for item in JUSTIFIED_EXCLUSIONS_SEED}
    assert set(exclusion_ids) == seed_ids
    kinds = {item["kind"] for item in exclusions}
    assert {
        "env-settings",
        "open-dict-typealias",
        "adapter-wire-models",
    } <= kinds


@pytest.mark.generated_artifact
def test_forbid_new_permissive_identities_after_baseline() -> None:
    """Any new effective-ignore under schemas/** outside registry (a) fails."""
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    baseline_debt = set(payload["migration_debt_identities"])
    live = build_payload()
    live_ignore = {
        row["identity"]
        for row in live["models"]
        if row["effective_extra"] == "ignore"
    }
    new_permissive = sorted(live_ignore - baseline_debt)
    assert new_permissive == [], (
        "Forbid-new permissive identities after RF-001 baseline; "
        f"unexpected effective-ignore models: {new_permissive}"
    )
    # Shrinking debt is allowed only via real migration (RF-002); RF-001 pins
    # exact set equality so accidental removals from the artifact without
    # code migration also fail the artifact-matches-generator gate.
    assert live_ignore == baseline_debt


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
    assert ingress["effective_extra"] == "ignore"
    assert DQ_YAML_INGRESS_IDENTITY in payload["migration_debt_identities"]

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
        assert identity in payload["migration_debt_identities"]
        assert "checks" in str(row.get("notes", "")) or identity.endswith(
            "SinkConfig"
        )

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
    assert BASE_API_CONFIG_IDENTITY in payload["migration_debt_identities"]
    # Must not appear in justified adapter-wire exclusion as a class identity.
    exclusion_ids = {item["identity"] for item in payload["justified_exclusions"]}
    assert BASE_API_CONFIG_IDENTITY not in exclusion_ids
    wire = next(
        item
        for item in payload["justified_exclusions"]
        if item["kind"] == "adapter-wire-models"
    )
    assert "BaseApiConfig" in wire["rationale"] or "Do not confuse" in wire["rationale"]
