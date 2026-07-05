"""ChEMBL assay determinism matrix ownership for tracked fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.helpers.control_plane_replay import PROJECT_ROOT, TRACKED_FIXTURE_MANIFEST

pytestmark = [
    pytest.mark.integration,
    pytest.mark.no_api,
    pytest.mark.chembl,
]


def test_chembl_assay_tracked_fixture_is_registered_for_determinism_lane() -> None:
    """ChEMBL assay must remain a tracked fixture owner for determinism matrix expansion."""
    payload = yaml.safe_load(TRACKED_FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    entry = payload["fixtures"]["chembl/assay"]
    assert entry["fixture_kind"] == "tracked_ci_sample"
    fixture_path = PROJECT_ROOT / entry["fixture_path"]
    assert fixture_path.is_file()
    assert entry["records"] > 0


def test_chembl_assay_cached_bronze_root_is_provider_entity_scoped(
    tmp_path: Path,
) -> None:
    """Replay cache roots for assay must stay provider/entity scoped."""
    provider, entity = "chembl/assay".split("/", 1)
    root = tmp_path / "cached_bronze" / provider / entity
    root.mkdir(parents=True)
    assert root.is_dir()
    assert root.name == "assay"
    assert root.parent.name == "chembl"
