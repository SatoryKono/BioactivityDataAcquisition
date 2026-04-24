from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "configs" / "base" / "bronze_fixture_manifest.yaml"
GAPS_PATH = PROJECT_ROOT / "configs" / "base" / "bronze_fixture_gaps.yaml"

REPLAY_CRITICAL_FAMILIES: dict[str, dict[str, object]] = {
    "chembl/assay": {
        "consumer_paths": (
            "tests/e2e/test_chembl_assay_e2e.py",
            "tests/e2e/test_pipeline_matrix_e2e.py",
        ),
    },
    "chembl/publication": {
        "consumer_paths": (
            "tests/e2e/test_chembl_publication_e2e.py",
            "tests/e2e/test_pipeline_matrix_e2e.py",
        ),
    },
    "chembl/target": {
        "consumer_paths": (
            "tests/e2e/test_chembl_target_e2e.py",
            "tests/e2e/test_full_pipeline_chain_e2e.py",
        ),
    },
    "pubchem/compound": {
        "consumer_paths": (
            "tests/e2e/test_pubchem_compound_e2e.py",
            "tests/integration/test_pubchem_pipeline.py",
        ),
    },
    "uniprot/protein": {
        "consumer_paths": (
            "tests/e2e/test_uniprot_protein_e2e.py",
            "tests/integration/test_uniprot_pipeline.py",
        ),
    },
}


def _load_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} must decode to a mapping"
    return payload


pytestmark = pytest.mark.no_api


def test_replay_critical_families_are_promoted_to_tracked_ci_samples() -> None:
    manifest = _load_yaml(MANIFEST_PATH).get("fixtures", {})
    gaps = _load_yaml(GAPS_PATH).get("gaps", {})
    assert isinstance(manifest, dict)
    assert isinstance(gaps, dict)

    for key in REPLAY_CRITICAL_FAMILIES:
        assert key not in gaps, f"{key} should not remain in bronze_fixture_gaps.yaml"

        entry = manifest.get(key)
        assert isinstance(entry, dict), f"Missing manifest entry for {key}"
        assert entry.get("fixture_kind") == "tracked_ci_sample"
        assert entry.get("validation_status") == "valid"

        fixture_path_raw = entry.get("fixture_path")
        assert isinstance(fixture_path_raw, str) and fixture_path_raw.startswith(
            "tests/fixtures/bronze/"
        )
        fixture_path = PROJECT_ROOT / fixture_path_raw
        assert fixture_path.exists(), f"Missing tracked fixture: {fixture_path_raw}"

        lines = fixture_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) >= 20, (
            f"{key} tracked fixture must contain at least 20 JSONL rows, "
            f"found {len(lines)}"
        )
        assert entry.get("records") == len(lines), (
            f"{key} manifest records field must match actual line count"
        )


def test_replay_critical_families_keep_ci_visible_consumer_paths() -> None:
    missing: list[str] = []

    for key, metadata in REPLAY_CRITICAL_FAMILIES.items():
        for rel_path in metadata["consumer_paths"]:
            path = PROJECT_ROOT / rel_path
            if not path.exists():
                missing.append(f"{key}: missing consumer path {rel_path}")

    assert not missing, "\n".join(missing)
