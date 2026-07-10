"""Golden contract tests for Bronze and Silver schema surfaces."""

from __future__ import annotations

import json
import os
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    load_snapshot,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]

GOLDEN_SCHEMA_DIR = Path("tests/fixtures/golden/schemas")
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"


def _dataclass_field_names(dataclass_type: type[object]) -> list[str]:
    return [field.name for field in fields(dataclass_type)]


def _assert_golden_payload(payload: dict[str, Any], fixture_path: Path) -> None:
    if UPDATE_SNAPSHOTS:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return

    if not fixture_path.exists():
        pytest.fail(
            f"Missing golden fixture {fixture_path}. "
            "Run with UPDATE_SNAPSHOTS=1 to create it."
        )

    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert payload == expected


def _bronze_schema_contract_payload() -> dict[str, Any]:
    from bioetl.infrastructure.storage.bronze.facade_contracts import (
        BRONZE_REQUIRED_METADATA_FIELDS,
        BRONZE_WRITE_ERRORS,
        BronzeWriterRuntimeServices,
    )
    from bioetl.infrastructure.storage.bronze.metadata_builders import (
        BronzeLineageMetadataRequest,
        BronzeMetadataPayloadRequest,
    )
    from bioetl.infrastructure.storage.bronze.pipeline_helpers import (
        BronzeWriteArtifacts,
        BronzeWritePostwriteContext,
        BronzeWritePrepared,
        BronzeWriteRequest,
    )

    return {
        "contract": "bronze_schema_contracts",
        "layer": "bronze",
        "version": 1,
        "file_contract": {
            "batch_filename_template": "batch_{YYYY-MM-DD}_{batch_id}.jsonl.zst",
            "record_encoding": "json-bytes",
            "sidecar_suffix": ".zst.meta.json",
            "compression": "zstd",
        },
        "required_metadata_fields": list(BRONZE_REQUIRED_METADATA_FIELDS),
        "write_error_types": sorted(
            error_type.__name__ for error_type in BRONZE_WRITE_ERRORS
        ),
        "dataclass_contracts": {
            "BronzeLineageMetadataRequest": _dataclass_field_names(
                BronzeLineageMetadataRequest
            ),
            "BronzeMetadataPayloadRequest": _dataclass_field_names(
                BronzeMetadataPayloadRequest
            ),
            "BronzeWriteArtifacts": _dataclass_field_names(BronzeWriteArtifacts),
            "BronzeWritePostwriteContext": _dataclass_field_names(
                BronzeWritePostwriteContext
            ),
            "BronzeWritePrepared": _dataclass_field_names(BronzeWritePrepared),
            "BronzeWriteRequest": _dataclass_field_names(BronzeWriteRequest),
            "BronzeWriterRuntimeServices": _dataclass_field_names(
                BronzeWriterRuntimeServices
            ),
        },
        "metadata_payload_sections": [
            "environment",
            "output",
            "output_ext",
            "pipeline",
            "runtime",
            "source",
        ],
    }


def _silver_schema_contract_payload() -> dict[str, Any]:
    snapshots_dir = Path("tests/contract/silver_schemas/snapshots")
    schemas: dict[str, dict[str, Any]] = {}
    for schema_name in sorted(SILVER_SCHEMAS):
        snapshot = load_snapshot(schema_name, snapshots_dir)
        if snapshot is None:
            pytest.fail(
                f"Missing Silver schema snapshot for {schema_name} in {snapshots_dir}"
            )
        schemas[schema_name] = {
            "field_count": len(snapshot),
            "fields": snapshot,
        }

    return {
        "contract": "silver_schema_contracts",
        "layer": "silver",
        "version": 1,
        "schema_count": len(schemas),
        "snapshot_source": "tests/contract/silver_schemas/snapshots",
        "schemas": schemas,
    }


def test_bronze_schema_contract_matches_golden_fixture() -> None:
    _assert_golden_payload(
        _bronze_schema_contract_payload(),
        GOLDEN_SCHEMA_DIR / "bronze_schema_contracts.json",
    )


def test_silver_schema_contract_matches_golden_fixture() -> None:
    _assert_golden_payload(
        _silver_schema_contract_payload(),
        GOLDEN_SCHEMA_DIR / "silver_schema_contracts.json",
    )
