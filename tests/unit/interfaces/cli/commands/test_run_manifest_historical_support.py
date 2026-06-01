"""Unit tests for historical replay CLI support helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.interfaces.cli.commands._run_manifest_historical_support import (
    _load_universe_external_records,
)


pytestmark = pytest.mark.unit

def test_load_universe_external_records_reads_archived_pack_fixture() -> None:
    pack_path = Path(
        "tests/fixtures/control_plane/historical_replay_universe/minimal_archive_pack.json"
    )

    records = _load_universe_external_records((pack_path,))

    assert len(records) == 1
    record = records[0]
    assert record.manifest_id == "archived-manifest-minimal"
    assert record.source_pack_ref == "archive-pack-minimal"
    assert record.durable_evidence_coverage is True


def test_load_universe_external_records_rejects_missing_required_fields(
    tmp_path: Path,
) -> None:
    pack_path = tmp_path / "invalid-pack.json"
    pack_path.write_text(
        json.dumps(
            {
                "pack_id": "invalid-pack",
                "records": [
                    {
                        "manifest_id": "missing-run-id",
                        "pipeline_name": "chembl_activity",
                        "provider": "chembl",
                        "entity": "activity",
                        "execution_context": "isolated",
                        "certification_status": "already_certified",
                        "replay_occurrence_kind": "historical_source_replay_certified_parent",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing fields: run_id"):
        _load_universe_external_records((pack_path,))
