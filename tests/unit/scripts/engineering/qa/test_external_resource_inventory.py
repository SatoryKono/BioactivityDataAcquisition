"""Isolated integrity controls for the COMP-004 source inventory (no runtime I/O)."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

import pytest

from scripts.engineering.qa.external_resource_inventory import (
    SCENARIOS,
    validate_inventory,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def inventory_case() -> tuple[dict[str, Any], dict[str, bytes], dict[str, str]]:
    """One real source expression; no product imports or external endpoints."""
    source = b"def acquire():\n    with open('fixture') as stream:\n        return stream.read()\n"
    path = "src/bioetl/fixture.py"
    blob = hashlib.sha1(
        b"blob " + str(len(source)).encode() + b"\0" + source
    ).hexdigest()
    reference = {
        "file": path,
        "line": 2,
        "source_commit": "a" * 40,
        "source_blob": blob,
        "content_sha256": hashlib.sha256(source).hexdigest(),
        "expression": "open('fixture')",
    }
    record = {
        "identity": "fixture.file",
        "type": "file",
        "creator": ["acquire"],
        "owner": "acquire operation",
        "closer": "file context exit",
        "shutdown_contract": "close on context exit",
        "production_entrypoint": "fixture.acquire",
        "call_path": ["acquire", "open"],
        "production_binding": [dict(reference)],
        "creation_sites": [reference],
        "qualification": "SOURCE_QUALIFIED_NOT_RUNTIME_VERIFIED",
        "scenarios": {
            name: {
                "applicability": "owner boundary",
                "expected": "close handle",
                "observation": "inspect handle after exit",
                "runtime_result": "NOT_RUN_12553",
            }
            for name in SCENARIOS
        },
    }
    payload = {
        "schema_version": 1,
        "source_commit": "a" * 40,
        "source_files": {path: blob},
        "resources": [record],
        "accepted_site_keys": [[path, 2, "open('fixture')"]],
        "prior_candidates_input": {"count": 1},
        "prior_candidate_dispositions": [
            {
                "candidate_id": "legacy-1",
                "object": "FixtureOwner",
                "file": path,
                "resource_definitions": ["fixture.file"],
            }
        ],
    }
    return payload, {path: source}, {path: blob}


def test_correct_inventory_is_accepted(inventory_case: tuple) -> None:
    assert validate_inventory(*inventory_case) == []


def test_duplicate_identity_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"].append(copy.deepcopy(payload["resources"][0]))
    assert any(
        "duplicate identity" in item
        for item in validate_inventory(payload, sources, blobs)
    )


@pytest.mark.parametrize("identity", [None, "", " "])
def test_missing_identity_is_rejected(inventory_case: tuple, identity: object) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["identity"] = identity
    assert "missing identity" in validate_inventory(payload, sources, blobs)


def test_missing_resource_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"] = []
    assert "missing resources" in validate_inventory(payload, sources, blobs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_commit", "b" * 40),
        ("source_blob", "c" * 40),
        ("content_sha256", "0" * 64),
        ("line", 20),
        ("expression", "open('different')"),
    ],
)
def test_inconsistent_source_provenance_is_rejected(
    inventory_case: tuple,
    field: str,
    value: object,
) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["creation_sites"][0][field] = value
    assert validate_inventory(payload, sources, blobs)


def test_changed_source_census_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    blobs["src/bioetl/new.py"] = "d" * 40
    sources["src/bioetl/new.py"] = b"pass\n"
    assert any("census" in item for item in validate_inventory(payload, sources, blobs))


def test_missing_acquisition_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["accepted_site_keys"].append(["src/bioetl/fixture.py", 3, "other()"])
    assert any(
        "coverage differs" in item
        for item in validate_inventory(payload, sources, blobs)
    )


def test_runtime_pass_cannot_be_invented(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["scenarios"]["normal"]["runtime_result"] = "PASS"
    assert any(
        "runtime result" in item for item in validate_inventory(payload, sources, blobs)
    )


def test_made_up_binding_provenance_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["resources"][0]["production_binding"] = [{"made_up_binding": True}]
    assert any(
        "provenance schema" in e for e in validate_inventory(payload, sources, blobs)
    )


def test_callback_location_and_expression_are_checked(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    site = payload["resources"][0]["creation_sites"][0]
    site.update(creation_mode="callback", line=1, expression="not a source expression")
    payload["accepted_site_keys"] = [[site["file"], 1, site["expression"]]]
    assert any(
        "source expression differs" in e
        for e in validate_inventory(payload, sources, blobs)
    )


def test_missing_history_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["prior_candidate_dispositions"] = []
    assert any(
        "historical candidate" in e for e in validate_inventory(payload, sources, blobs)
    )


def test_duplicate_history_identity_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    payload["prior_candidates_input"]["count"] = 2
    payload["prior_candidate_dispositions"] *= 2
    assert any(
        "historical candidate" in e for e in validate_inventory(payload, sources, blobs)
    )


def test_missing_unreferenced_source_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    name = "src/bioetl/unreferenced.py"
    blobs[name] = hashlib.sha1(b"blob 5\0pass\n").hexdigest()
    payload["source_files"] = dict(blobs)
    assert any(
        "missing source content" in e
        for e in validate_inventory(payload, sources, blobs)
    )


def test_partitioned_catalog_roundtrip(inventory_case: tuple, tmp_path: Any) -> None:
    from scripts.engineering.qa.external_resource_inventory import (
        load_catalog,
        write_catalog,
    )

    payload, _, _ = inventory_case
    write_catalog(payload, tmp_path)
    loaded = load_catalog(tmp_path)
    assert loaded["resources"] == payload["resources"]
    assert loaded["source_files"] == payload["source_files"]


def test_partition_digest_rejects_changed_content(
    inventory_case: tuple, tmp_path: Any
) -> None:
    from scripts.engineering.qa.external_resource_inventory import (
        load_catalog,
        write_catalog,
    )

    payload, _, _ = inventory_case
    write_catalog(payload, tmp_path)
    part = tmp_path / "configs/quality/external_resource_inventory/part-01.json"
    part.write_bytes(part.read_bytes() + b" ")
    with pytest.raises(ValueError, match="digest"):
        load_catalog(tmp_path)


def test_partition_path_escape_is_rejected(
    inventory_case: tuple, tmp_path: Any
) -> None:
    import json
    from scripts.engineering.qa.external_resource_inventory import (
        CATALOG,
        load_catalog,
        write_catalog,
    )

    payload, _, _ = inventory_case
    write_catalog(payload, tmp_path)
    index = tmp_path / CATALOG
    data = json.loads(index.read_text())
    data["resource_parts"][0]["file"] = "outside.json"
    index.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outside"):
        load_catalog(tmp_path)


def test_duplicate_partition_is_rejected(inventory_case: tuple, tmp_path: Any) -> None:
    import json
    from scripts.engineering.qa.external_resource_inventory import (
        CATALOG,
        load_catalog,
        write_catalog,
    )

    payload, _, _ = inventory_case
    write_catalog(payload, tmp_path)
    index = tmp_path / CATALOG
    data = json.loads(index.read_text())
    data["resource_parts"] *= 2
    index.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="duplicated"):
        load_catalog(tmp_path)


def test_changed_working_source_is_rejected(inventory_case: tuple) -> None:
    payload, sources, blobs = inventory_case
    sources["src/bioetl/fixture.py"] = sources["src/bioetl/fixture.py"].replace(
        b"return", b"yield"
    )
    assert any(
        "content changed" in item
        for item in validate_inventory(payload, sources, blobs)
    )
