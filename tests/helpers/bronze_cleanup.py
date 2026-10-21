"""Synthetic writer ownership attestations for public cleanup tests."""

import hashlib
import json

from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.infrastructure.storage.bronze.facade_contracts import (
    BronzeWriterRuntimeServices,
)


def sidecar_bytes(
    data: bytes,
    artifact: str,
    copy: bytes | None = None,
    *,
    provider: str = "chembl",
    entity: str = "activity",
) -> bytes:
    return json.dumps(
        {
            "provider": provider,
            "entity": entity,
            "batch_id": artifact[17:].split(".jsonl", 1)[0],
            "cleanup_association": {
                "schema": 1,
                "payload_sha256": hashlib.sha256(data).hexdigest(),
                "copy_sha256": hashlib.sha256(copy).hexdigest()
                if copy is not None
                else None,
            },
        },
        sort_keys=True,
    ).encode()


def flat_owner_services() -> BronzeWriterRuntimeServices:
    """Synthetic flat-cleanup owner, independent of sidecar metadata."""
    return BronzeWriterRuntimeServices(
        tracing=None,
        audit=None,
        metadata_writer=NoOpMetadataWriter(),
        save_metadata=False,
        metadata_coordinator=None,
        root_identity=("chembl", "activity"),
    )
