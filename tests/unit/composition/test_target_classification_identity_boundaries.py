"""Public runtime identity boundaries; synthetic profiles confer no admission."""

from __future__ import annotations

from dataclasses import replace

import pytest

from bioetl.composition.runtime_builders.config_access import load_pipeline_config
from bioetl.composition.bootstrap.assembly.target_classification_identity import (
    apply_target_contract_identity,
    target_classification_contract_schema_identity,
    target_classification_normalization_identity,
    target_classification_source_refs,
)
from bioetl.composition.bootstrap.assembly.storage import (
    build_target_classification_session,
    load_target_runtime_profile,
)
from bioetl.composition.bootstrap.assembly.target_classification_runtime import (
    validate_target_runtime_dependency,
)
from bioetl.domain.contracts.gold.chembl_target_classification import (
    target_v31_schema_hash,
)
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.infrastructure.config.contract_identity_resolution import (
    resolve_contract_identity,
)
from iuphar_target_class.matching import (
    MATCHING_POLICY_ROLE_SEPARATED_V2,
    profile_qualifies_matching_policy,
)
from tests.helpers.iuphar_snapshot import synthetic_snapshot_bundle

pytestmark = pytest.mark.unit


def _mode(config, mode):
    return config.model_copy(
        update={
            "target_classification": config.target_classification.model_copy(
                update={"mode": mode}
            )
        }
    )


@pytest.mark.parametrize("mode", ["off", "shadow", "enrich"])
def test_selected_contract_identity_preserves_dq_and_legacy_modes(mode):
    config = _mode(load_pipeline_config("chembl_target"), mode)
    original = resolve_contract_identity(
        provider="chembl", entity="target", strict=True
    )
    selected = apply_target_contract_identity(config, original)
    if mode != "enrich":
        assert selected is original
        assert target_classification_contract_schema_identity(config) is None
        assert target_classification_normalization_identity(config) is None
        return
    normalization = target_v31_normalization_profile().identity
    assert selected == replace(
        original,
        contract_version="3.1.0",
        contract_schema_hash=target_v31_schema_hash(),
        normalization_profile_ref=normalization.profile_name,
        normalization_profile_version=normalization.profile_version,
        normalization_profile_hash=normalization.profile_hash,
    )
    assert selected.dq_policy_ref == original.dq_policy_ref
    assert selected.rule_bundle_version == original.rule_bundle_version
    assert selected.contract_ref == original.contract_ref


def test_disabled_or_unrelated_config_has_no_classification_dependency():
    config = load_pipeline_config("chembl_target")
    assert load_target_runtime_profile(config) is None
    assert build_target_classification_session(config, object()) is None
    assert target_classification_source_refs(config) == ()
    assert target_classification_source_refs(object()) == ()
    assert target_classification_contract_schema_identity(object()) is None
    assert target_classification_normalization_identity(object()) is None
    assert validate_target_runtime_dependency(object()) is None


def test_relative_profile_uses_actual_configs_parent_and_checks_frozen_bytes(
    tmp_path, monkeypatch
):
    root, bundle = synthetic_snapshot_bundle(tmp_path / "frozen")
    config = load_pipeline_config("chembl_target")
    config = config.model_copy(
        update={
            "target_classification": config.target_classification.model_copy(
                update={
                    "mode": "shadow",
                    "snapshot_manifest": str(
                        (root / "profile.json").relative_to(tmp_path)
                    ),
                    "snapshot_manifest_sha256": bundle.profile_sha256,
                }
            )
        }
    )
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.resolve_configs_root",
        lambda: tmp_path / "configs",
    )
    profile = load_target_runtime_profile(config)
    assert profile.profile_uri == (root / "profile.json").as_uri()
    assert profile.profile_sha256 == bundle.profile_sha256
    (root / "profile.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_target_runtime_profile(config)


def test_historical_profile_does_not_qualify_role_separated_matching():
    identity = target_v31_normalization_profile().identity
    assert (
        profile_qualifies_matching_policy(
            profile_name=identity.profile_name,
            profile_version=identity.profile_version,
            profile_hash=identity.profile_hash,
            matching_policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
        )
        is False
    )
    config = _mode(load_pipeline_config("chembl_target"), "enrich")
    original = resolve_contract_identity(
        provider="chembl", entity="target", strict=True
    )
    selected = apply_target_contract_identity(config, original)
    assert selected.normalization_profile_hash == identity.profile_hash
    assert selected.normalization_profile_version == identity.profile_version
    assert MATCHING_POLICY_ROLE_SEPARATED_V2 not in {
        selected.contract_version,
        selected.normalization_profile_version,
        selected.normalization_profile_hash,
        selected.normalization_profile_ref,
    }


def test_unqualified_profile_cannot_select_role_separated_matching(tmp_path):
    import hashlib
    import json

    from bioetl.infrastructure.adapters.iuphar.acceptance_receipt import load_profile
    from iuphar_target_class.bioetl_input import UNIPROT_PROJECTION_POLICY_V1
    from iuphar_target_class.matching import MATCHING_POLICY_STRICT_ANCHORS_V1

    root, bundle = synthetic_snapshot_bundle(tmp_path / "frozen")
    loaded = load_profile(
        root / "profile.json", bundle.profile_sha256, require_acceptance=False
    )
    assert loaded.matching_policy == MATCHING_POLICY_STRICT_ANCHORS_V1
    assert loaded.uniprot_projection_policy == UNIPROT_PROJECTION_POLICY_V1
    document = json.loads((root / "profile.json").read_text(encoding="utf-8"))
    document["matching_policy"] = MATCHING_POLICY_ROLE_SEPARATED_V2
    payload = json.dumps(document).encode("utf-8")
    (root / "profile.json").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    with pytest.raises(ValueError, match="does not qualify role-separated matching"):
        load_profile(root / "profile.json", digest, require_acceptance=False)
