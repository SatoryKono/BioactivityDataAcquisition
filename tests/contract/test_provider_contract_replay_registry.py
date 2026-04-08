"""Registry checks for provider contract replay coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from tests.contract._provider_contract_replay import PROVIDER_CONTRACT_REPLAY_PROBES

ROOT = Path(__file__).resolve().parents[2]
TEST_MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"

pytestmark = [pytest.mark.no_api, pytest.mark.contracts]


def test_replay_registry_covers_all_required_snapshot_probes() -> None:
    payload = cast(
        dict[str, Any], yaml.safe_load(TEST_MATRIX_PATH.read_text(encoding="utf-8"))
    )
    registry = cast(
        dict[str, Any], payload["fixture_governance"]["contract_snapshot_registry"]
    )
    expected = {
        (provider, probe)
        for provider, provider_payload in cast(
            dict[str, dict[str, Any]], registry["providers"]
        ).items()
        for probe in cast(list[str], provider_payload["required_probes"])
    }
    actual = {(case.provider, case.probe) for case in PROVIDER_CONTRACT_REPLAY_PROBES}

    assert actual == expected


def test_replay_registry_points_to_existing_cassettes() -> None:
    for case in PROVIDER_CONTRACT_REPLAY_PROBES:
        assert case.cassette_path.exists(), case.cassette_rel_path
