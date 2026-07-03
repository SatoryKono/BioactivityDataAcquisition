"""Idempotency gate for tracked-fixture manifest fingerprints across providers."""

from __future__ import annotations

import pytest
import yaml

from tests.helpers.control_plane_replay import PROJECT_ROOT, TRACKED_FIXTURE_MANIFEST
from tests.integration.determinism.test_reproducibility_determinism_gate import (
    _canonical_manifest_fingerprint,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.no_api,
]


def _stable_manifest(*, provider: str, entity: str, fingerprint: str) -> dict:
    return {
        "execution_fingerprint": fingerprint,
        "provider": provider,
        "entity": entity,
        "replay_capability": "exact_replay_supported",
        "launch_context": {
            "exact_replay": True,
            "execution_context": "cached_fixture",
            "required_persistence_profile": "degraded_observable",
        },
        "runtime_config": {
            "exact_replay": True,
            "execution_context": "cached_fixture",
            "required_persistence_profile": "degraded_observable",
        },
        "code_provenance": {
            "contract_ref": f"{provider}/{entity}/gold",
            "config_hash": "cfg-hash",
            "effective_config_artifact_id": "cfg-artifact",
            "dq_contract_compatibility_hash": "dq-hash",
        },
        "source_refs": [{"provider": provider, "entity": entity}],
    }


def test_pubchem_compound_tracked_fixture_is_registered_for_idempotency_lane() -> None:
    """PubChem compound remains a tracked fixture owner beyond the ChEMBL activity gate."""
    payload = yaml.safe_load(TRACKED_FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    entry = payload["fixtures"]["pubchem/compound"]
    assert entry["fixture_kind"] == "tracked_ci_sample"
    fixture_path = PROJECT_ROOT / entry["fixture_path"]
    assert fixture_path.is_file()


def test_pubchem_compound_manifest_fingerprint_is_idempotent_across_replays() -> None:
    """Repeated fingerprinting of the same pubchem manifest payload is bit-stable."""
    manifest = _stable_manifest(
        provider="pubchem",
        entity="compound",
        fingerprint="fp-pubchem-compound-1",
    )
    fingerprints = [_canonical_manifest_fingerprint(manifest) for _ in range(3)]
    assert fingerprints[0] == fingerprints[1] == fingerprints[2]
    assert len(fingerprints[0]) == 64


def test_chembl_activity_and_pubchem_compound_fingerprints_differ() -> None:
    """Idempotency gate covers a second provider without collapsing fingerprints."""
    chembl = _canonical_manifest_fingerprint(
        _stable_manifest(
            provider="chembl",
            entity="activity",
            fingerprint="fp-shared",
        )
    )
    pubchem = _canonical_manifest_fingerprint(
        _stable_manifest(
            provider="pubchem",
            entity="compound",
            fingerprint="fp-shared",
        )
    )
    assert chembl != pubchem
