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
"""Owning ratchet + registry (b) anchors for PSC RF-003 (#12568).

RF-003 does **not** own remaining code migration. Migration debt (a) must
already be the exact empty set after RF-002. This module locks:

* exact identity-set ratchet (debt=[] ; forbid-new ceiling frozen)
* finalized justified exclusions (b) with rationale + live anchor tests
* nested typo → ``extra_forbidden`` on strict boundaries
* open-dict classification keeps open semantics without weakening parent forbid

Moving a model into registry (b) is reclassification, not debt clear.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bioetl.domain.types.identifiers import JsonDict
from bioetl.infrastructure.adapters.pubchem.models import PubchemMoleculeApiRecord
from bioetl.infrastructure.config._base import Settings
from bioetl.infrastructure.schemas.base_schemas_chembl import BaseApiConfig
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile
from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
    InputFilterYamlConfig,
    MaintenanceConfig,
    SinkDQReportConfig,
    SinkLayerConfig,
    TransformConfig,
)
from tests.architecture._config_extra_forbid_inventory import (
    BASE_API_CONFIG_IDENTITY,
    BASELINE_SHA,
    DEFAULT_JSON_OUTPUT,
    FILTER_CONFIG_METADATA_IDENTITY,
    FILTER_CONFIG_METADATA_PATH,
    FILTER_CONFIG_ROOT,
    JUSTIFIED_EXCLUSIONS,
    RF001_FORBID_NEW_BASELINE_IDENTITIES,
    RF002_DEBT_CLEARED_SHA,
    RF003_ISSUE_ID,
    RF003_REQUIRED_EXCLUSION_KINDS,
    build_payload,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "reports" / "quality" / "config-extra-forbid-inventory.json"
PIPELINE_SCHEMA = ROOT / "configs" / "_schema" / "pipeline.json"


def _assert_extra_forbidden(exc_info: pytest.ExceptionInfo[ValidationError]) -> None:
    assert any(err["type"] == "extra_forbidden" for err in exc_info.value.errors())


@pytest.mark.generated_artifact
def test_rf003_migration_debt_remains_exact_empty_set() -> None:
    """Registry (a) must stay exact empty identity set — no countdown soft ratchet."""
    assert INVENTORY_PATH == DEFAULT_JSON_OUTPUT
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    live = build_payload()
    debt = payload["migration_debt_identities"]
    assert debt == []
    assert debt == live["migration_debt_identities"]
    assert debt == sorted(debt)
    assert payload["counts"]["effective_ignore"] == 0
    assert payload["counts"]["effective_forbid"] == 105
    assert payload["rf002_debt_cleared_sha"] == RF002_DEBT_CLEARED_SHA
    assert payload["baseline_sha"] == BASELINE_SHA
    assert payload["rf003_issue"] == RF003_ISSUE_ID


@pytest.mark.generated_artifact
def test_rf003_forbid_new_permissive_identities_exact_ceiling() -> None:
    """Cannot add a new schemas/** effective-ignore identity under the RF-001 ceiling."""
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    frozen = RF001_FORBID_NEW_BASELINE_IDENTITIES
    assert set(payload["forbid_new_baseline_identities"]) == frozen
    assert len(frozen) == 36
    live = build_payload()
    live_ignore = {
        row["identity"] for row in live["models"] if row["effective_extra"] == "ignore"
    }
    assert live_ignore == set()
    assert live_ignore <= frozen
    new_permissive = sorted(live_ignore - frozen)
    assert new_permissive == []


@pytest.mark.generated_artifact
def test_rf003_justified_exclusions_finalized_with_anchors() -> None:
    """Registry (b) is finalized: required kinds, rationale, anchor + anchor_test."""
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    exclusions = payload["justified_exclusions"]
    expected_ids = sorted(item["identity"] for item in JUSTIFIED_EXCLUSIONS)
    actual_ids = [item["identity"] for item in exclusions]
    assert actual_ids == expected_ids
    assert actual_ids == sorted(actual_ids)

    debt = set(payload["migration_debt_identities"])
    assert set(actual_ids).isdisjoint(debt)

    kinds = {item["kind"] for item in exclusions}
    assert RF003_REQUIRED_EXCLUSION_KINDS <= kinds

    for item in exclusions:
        assert item["rationale"].strip()
        assert item["anchor"]
        assert item["anchor_test"].startswith("tests/architecture/")
        assert "::test_" in item["anchor_test"]
        anchor_path = ROOT / item["anchor"]
        # Glob-style adapter path ends with /
        if item["anchor"].endswith("/"):
            assert anchor_path.is_dir(), item["anchor"]
        else:
            assert anchor_path.is_file(), item["anchor"]

    # Moving into (b) ≠ clearing debt: debt empty AND (b) identities are not
    # schemas/** effective-ignore rows (they live outside migration debt scan).
    schemas_identities = {row["identity"] for row in payload["models"]}
    for item in exclusions:
        if item["kind"] in {"env-settings", "open-dict-typealias", "adapter-wire-models"}:
            assert item["identity"] not in schemas_identities
        if item["kind"] == "open-dict-field":
            # Field path is not a BaseModel identity in the schemas scan.
            assert item["identity"] not in schemas_identities
            assert item["identity"].endswith(".metadata")


def test_registry_b_settings_anchor_ignores_unknown_keys() -> None:
    """Settings (env surface) keeps extra=ignore; unknown keys do not fail."""
    assert Settings.model_config.get("extra") == "ignore"
    settings = Settings(
        test_mode=True,
        _env_file=None,
        rf003_unknown_settings_key="ignored",
    )
    assert settings.test_mode is True
    assert not hasattr(settings, "rf003_unknown_settings_key")


def test_registry_b_jsondict_open_semantics_and_parent_strictness() -> None:
    """JsonDict stays open; parent forbid paths still reject unknown siblings."""
    # Type alias remains an open dict (not a BaseModel forbid boundary).
    sample: JsonDict = {"arbitrary_rf003_key": 1, "nested": {"x": True}}
    assert sample["arbitrary_rf003_key"] == 1

    schema = json.loads(PIPELINE_SCHEMA.read_text(encoding="utf-8"))
    defs = schema.get("$defs") or schema.get("definitions") or {}
    assert "JsonDict" in defs
    assert defs["JsonDict"].get("additionalProperties") is True

    # Parent SinkLayerConfig (forbid) rejects unknown sibling even with open child.
    good = {
        "path": "data/output/bronze",
        "format": "jsonl",
        "dq_report": {"enabled": True, "format": "json"},
    }
    SinkLayerConfig.model_validate(good)
    with pytest.raises(ValidationError) as exc_info:
        SinkLayerConfig.model_validate({**good, "rf003_parent_typo": True})
    _assert_extra_forbidden(exc_info)


def test_registry_b_adapter_wire_ignores_extras_not_base_api() -> None:
    """Adapter wire keeps extra=ignore; BaseApiConfig stays forbid (not wire)."""
    assert PubchemMoleculeApiRecord.model_config.get("extra") == "ignore"
    wire = PubchemMoleculeApiRecord.model_validate(
        {"cid": 42, "rf003_wire_extra": "tolerated"}
    )
    assert wire.cid == 42

    assert BaseApiConfig.model_config.get("extra") == "forbid"
    with pytest.raises(ValidationError) as exc_info:
        BaseApiConfig.model_validate(
            {"base_url": "https://example.test", "rf003_not_wire": 1}
        )
    _assert_extra_forbidden(exc_info)

    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert BASE_API_CONFIG_IDENTITY not in {
        item["identity"] for item in payload["justified_exclusions"]
    }
    assert BASE_API_CONFIG_IDENTITY not in payload["migration_debt_identities"]


def test_registry_b_filter_config_metadata_open_dict() -> None:
    """FilterConfigFile.metadata is open JsonDict; unknown siblings stay forbid."""
    payload = {
        "version": "1.0.0",
        "provider": "chembl",
        "entity": "target",
        "input_filter": {"enabled": False},
        "metadata": {
            "target_filter_policy": {"scope": "source_specific"},
            "rf003_open_nested": {"accepted": True},
        },
    }
    config = FilterConfigFile.model_validate(payload)
    assert config.metadata["rf003_open_nested"]["accepted"] is True
    _input, _silver, _gold, extraction = config.to_domain()
    assert extraction.params == {}

    with pytest.raises(ValidationError) as exc_info:
        FilterConfigFile.model_validate({**payload, "rf003_unknown_sibling": True})
    _assert_extra_forbidden(exc_info)


@pytest.mark.generated_artifact
def test_rf003_filter_config_metadata_nested_path_is_justified_exclusion() -> None:
    """JsonDict metadata must appear in nested_paths as justified-exclusion edge.

    ``_walk_nested_paths`` only yields BaseModel children; the open field needs an
    explicit inventory edge linked to JUSTIFIED_EXCLUSIONS (Devin #discussion_r4390779006).
    """
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    live = build_payload()
    exclusion_ids = {item["identity"] for item in JUSTIFIED_EXCLUSIONS}
    assert FILTER_CONFIG_METADATA_IDENTITY in exclusion_ids

    edge_rows = [
        row
        for row in payload["nested_paths"]
        if row["root"] == FILTER_CONFIG_ROOT
        and row["path"] == FILTER_CONFIG_METADATA_PATH
    ]
    assert edge_rows, (
        "nested_paths missing FilterConfigFile.metadata open-dict edge"
    )
    assert len(edge_rows) == 1
    edge = edge_rows[0]
    assert edge["identity"] == FILTER_CONFIG_METADATA_IDENTITY
    assert edge["classification"] == "justified-exclusion"
    assert edge["effective_extra"] == "open"
    assert edge["role"] == "open-dict-field"
    assert edge.get("edge_kind") == "explicit-open-dict-field"
    assert edge["identity"] in {
        item["identity"] for item in payload["justified_exclusions"]
    }

    live_edges = [
        row
        for row in live["nested_paths"]
        if row["root"] == FILTER_CONFIG_ROOT
        and row["path"] == FILTER_CONFIG_METADATA_PATH
    ]
    assert live_edges == edge_rows


@pytest.mark.parametrize(
    ("model", "good"),
    [
        (InputFilterYamlConfig, {"enabled": False}),
        (MaintenanceConfig, {}),
        (TransformConfig, {}),
        (SinkDQReportConfig, {"enabled": True, "format": "json"}),
        (FilterConfigFile, {"version": "1.0.0"}),
    ],
)
def test_rf003_nested_typo_extra_forbidden_on_strict_boundaries(
    model: type,
    good: dict[str, object],
) -> None:
    """Strict classified boundaries: nested typo → extra_forbidden (not silent)."""
    model.model_validate(good)
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate({**good, "rf003_nested_typo": 1})
    _assert_extra_forbidden(exc_info)


def test_rf003_open_dict_classification_does_not_require_key_rejection() -> None:
    """Open-dict classification: unknown keys inside metadata are accepted."""
    config = FilterConfigFile.model_validate(
        {
            "version": "1.0.0",
            "metadata": {"brand_new_policy_key": {"enabled": True}},
        }
    )
    assert config.metadata["brand_new_policy_key"]["enabled"] is True
