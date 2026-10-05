"""Create-only parent replay envelopes and verified logical table artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import cast

import orjson
import pyarrow as pa

from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    ProteinClassTopLevelMappingEntry,
)
from bioetl.domain.normalization.json import serialize_json_canonical
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.composite_replay_inputs import _table_bytes

SUPPORTED_COMPOSITES = frozenset(
    f"composite_{name}"
    for name in ("activity", "assay", "molecule", "publication", "target")
)


def digest_bytes(content: bytes) -> str:
    """Return a portable SHA256 digest."""
    return hashlib.sha256(content).hexdigest()


def implementation_fingerprint() -> str:
    """Bind replay to the installed implementation, independent of Git metadata."""
    package = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    for path in sorted(package.rglob("*.py")):
        digest.update(path.relative_to(package).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def publish_bytes(root: Path, name: str, content: bytes) -> str:
    """Write one new object; reject escaping paths and previous evidence."""
    path = confined_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)
    return digest_bytes(content)


def confined_path(root: Path, name: str) -> Path:
    """Resolve a strictly relative object reference within its evidence root."""
    path = (root / name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError("composite_replay_path_escape")
    return path


def publish_json(root: Path, name: str, payload: JsonDict) -> str:
    """Publish canonical JSON without lossy fallback serialization."""
    return publish_bytes(
        root,
        name,
        serialize_json_canonical(payload).encode(),
    )


def load_verified_json(root: Path, name: str, digest: str) -> JsonDict:
    """Read an identity-bound JSON object."""
    content = confined_path(root, name).read_bytes()
    if digest_bytes(content) != digest:
        raise ValueError("composite_replay_digest_mismatch")
    value = orjson.loads(content)
    if not isinstance(value, dict):
        raise ValueError("composite_replay_envelope_invalid")
    return cast(JsonDict, value)


def canonical_table(table: pa.Table) -> pa.Table:
    """Normalize physical Delta row ordering using the assay identity contract."""
    keys = [
        name
        for name in ("entity_id", "chembl.assay.assay_id", "assay_id")
        if name in table.column_names
    ]
    if not keys or table.num_rows == 0:
        raise ValueError("composite_replay_output_identity_missing")
    return (
        table.sort_by([(name, "ascending") for name in keys])
        .combine_chunks()
        .replace_schema_metadata(None)
    )


def publish_table(root: Path, name: str, table: pa.Table) -> str:
    """Save the logical table read from a completed physical output."""
    return publish_bytes(root, name, _table_bytes(canonical_table(table)))


def verify_bundle(root: Path, envelope_digest: str) -> JsonDict:
    """Re-check every mandatory object; historical success does not bypass loss."""
    envelope = load_verified_json(root, "parent.json", envelope_digest)
    version = envelope.get("version")
    if version not in {"assay-parent-replay-v1", "composite-parent-replay-v2"}:
        raise ValueError("composite_replay_version_invalid")
    allowed = (
        {"composite_assay"}
        if version == "assay-parent-replay-v1"
        else SUPPORTED_COMPOSITES
    )
    if envelope.get("pipeline") not in allowed:
        raise ValueError("composite_replay_family_invalid")
    objects = envelope.get("objects")
    if not isinstance(objects, dict) or not objects:
        raise ValueError("composite_replay_objects_missing")
    required = {
        "config.json",
        "uv.lock",
        "pipeline-settings.json",
        "expected/silver.arrow",
        "expected/gold.arrow",
        "inputs/inputs.json",
    }
    if version == "composite-parent-replay-v2":
        required.add("field-groups.json")
    if envelope.get("pipeline") == "composite_target":
        required.add("target-mapping.json")
    if not required.issubset(objects) or objects["inputs/inputs.json"] != envelope.get(
        "input_snapshot_fingerprint"
    ):
        raise ValueError("composite_replay_required_object_missing")
    _verify_objects(root, objects)
    if envelope.get("implementation") != implementation_fingerprint():
        raise ValueError("composite_replay_implementation_mismatch")
    return envelope


def _verify_objects(root: Path, objects: JsonDict) -> None:
    """Check every sealed object's reference, type and actual bytes."""
    for name, digest in objects.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            raise ValueError("composite_replay_object_invalid")
        if digest_bytes(confined_path(root, name).read_bytes()) != digest:
            raise ValueError("composite_replay_object_digest_mismatch")
        if name == "target-mapping.json":
            _verify_target_mapping(load_verified_json(root, name, digest))


def _verify_target_mapping(payload: JsonDict) -> None:
    """Reject sealed mapping data that cannot restore the target collaborator."""
    version = payload.get("mapping_version")
    entries = payload.get("entries")
    ignored = payload.get("non_counting_classes")
    if not isinstance(version, str) or not isinstance(entries, list):
        raise ValueError("composite_replay_target_mapping_invalid")
    if not isinstance(ignored, list) or not all(isinstance(x, str) for x in ignored):
        raise ValueError("composite_replay_target_mapping_invalid")
    restored = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "raw_label",
            "canonical_l1",
            "counts_for_target_type",
        }:
            raise ValueError("composite_replay_target_mapping_invalid")
        raw, canonical, counting = (
            entry["raw_label"],
            entry["canonical_l1"],
            entry["counts_for_target_type"],
        )
        if (
            not isinstance(raw, str)
            or not isinstance(canonical, str)
            or not isinstance(counting, bool)
        ):
            raise ValueError("composite_replay_target_mapping_invalid")
        restored.append(ProteinClassTopLevelMappingEntry(raw, canonical, counting))
    ProteinClassTargetTypeMappingData(version, tuple(restored), frozenset(ignored))
