"""Writer-produced content association on synthetic temporary Bronze roots."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze import cleanup_group_journal as journal
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

pytestmark = pytest.mark.integration

BATCH = "11111111-1111-4111-8111-111111111111"


@pytest.mark.asyncio
@pytest.mark.parametrize("save_json", [False, True])
@pytest.mark.parametrize("flat_structure", [False, True])
async def test_writer_attests_exact_payload_and_optional_copy(
    tmp_path: Path, save_json: bool, flat_structure: bool
) -> None:
    writer = BronzeWriter(
        base_path=tmp_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(save_json, None),
        flat_structure=flat_structure,
    )
    arguments = {
        "provider": "chembl",
        "entity": "activity",
        "date": datetime(2024, 1, 1, tzinfo=UTC),
        "batch_id": BatchID(UUID(BATCH)),
        "run_id": RunID(UUID("22222222-2222-4222-8222-222222222222")),
        "run_type": RunType.INCREMENTAL,
        "ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC),
    }
    result = await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    payload = tmp_path / result.relative_path
    sidecar = Path(f"{payload}.meta.json")
    metadata = json.loads(sidecar.read_bytes())
    association = metadata["cleanup_association"]
    assert (
        association["payload_sha256"]
        == hashlib.sha256(payload.read_bytes()).hexdigest()
    )
    copy = payload.with_suffix("")
    assert association["copy_sha256"] == (
        hashlib.sha256(copy.read_bytes()).hexdigest() if save_json else None
    )
    original = sidecar.read_bytes()
    await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    assert sidecar.read_bytes() == original
    toggled = BronzeWriter(
        base_path=tmp_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(not save_json, None),
        flat_structure=flat_structure,
    )
    await toggled.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    assert sidecar.read_bytes() == original
    if not save_json:
        # Enabling JSON export on retry must not adopt a formerly unattested copy.
        spec = journal.GroupSpec(
            "chembl", "activity", "2024-01-01", BATCH, "2024-01-02", flat_structure
        )
        with pytest.raises(journal.GroupJournalConflict, match="unassociated"):
            journal._validate_association(
                metadata,
                spec,
                {
                    "payload": {
                        "sha256": hashlib.sha256(payload.read_bytes()).hexdigest()
                    },
                    "copy": {"sha256": hashlib.sha256(copy.read_bytes()).hexdigest()},
                },
            )
    # Legacy retries remain valid; they do not acquire cleanup ownership.
    del metadata["cleanup_association"]
    legacy = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    sidecar.write_bytes(legacy)
    await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    assert sidecar.read_bytes() == legacy


@pytest.mark.parametrize(
    "mutation", ["legacy", "payload", "copy", "scope", "schema", "digest"]
)
def test_association_rejects_unattested_or_foreign_content(mutation: str) -> None:
    spec = journal.GroupSpec("chembl", "activity", "2024-01-01", BATCH, "2024-01-02")
    metadata = {
        "provider": "chembl",
        "entity": "activity",
        "batch_id": BATCH,
        "cleanup_association": {
            "schema": 1,
            "payload_sha256": "a" * 64,
            "copy_sha256": "b" * 64,
        },
    }
    members = {"payload": {"sha256": "a" * 64}, "copy": {"sha256": "b" * 64}}
    journal._validate_association(metadata, spec, members)
    if mutation == "legacy":
        del metadata["cleanup_association"]
    elif mutation == "scope":
        metadata["provider"] = "foreign"
    elif mutation == "schema":
        metadata["cleanup_association"]["schema"] = True
    elif mutation == "digest":
        del members["copy"]
        metadata["cleanup_association"]["copy_sha256"] = "invalid"
    else:
        members[mutation]["sha256"] = "c" * 64
    with pytest.raises(journal.GroupJournalConflict, match="unassociated"):
        journal._validate_association(metadata, spec, members)
