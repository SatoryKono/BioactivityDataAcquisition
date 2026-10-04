"""Bind immutable replay artifacts to parent reports and strict HTTP projection."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.composite_replay_bundle import (
    SUPPORTED_COMPOSITES,
    confined_path,
    digest_bytes,
    load_verified_json,
    verify_bundle,
)


_PARENT_ENVELOPE_FILE = "parent.json"
_VERIFICATION_RECEIPT_FILE = "verification/verification.json"


def replay_artifacts(
    root: Path | None, pipeline: str, run_id: str
) -> tuple[JsonDict, ...]:
    """Enumerate only a fully verified capture; incomplete runs get no capability."""
    if root is None or pipeline not in SUPPORTED_COMPOSITES:
        return ()
    replay = root / "pipeline" / pipeline / run_id / "replay"
    parent = replay / _PARENT_ENVELOPE_FILE
    receipt_path = replay / "verification" / "verification.json"
    if not parent.is_file() or not receipt_path.is_file():
        return ()
    envelope_hash = digest_bytes(parent.read_bytes())
    envelope = verify_bundle(replay, envelope_hash)
    receipt_hash = digest_bytes(receipt_path.read_bytes())
    receipt = load_verified_json(replay, _VERIFICATION_RECEIPT_FILE, receipt_hash)
    _verify_receipt(replay, envelope_hash, run_id, receipt)
    references = {
        _PARENT_ENVELOPE_FILE: envelope_hash,
        _VERIFICATION_RECEIPT_FILE: receipt_hash,
        **envelope["objects"],
        **{
            f"verification/{name}": digest
            for name, digest in receipt["objects"].items()
        },
    }
    return tuple(
        {
            "kind": "composite_exact_replay"
            if name == _PARENT_ENVELOPE_FILE
            else "composite_replay_object",
            "ref": f"replay/{name}",
            "sha256": digest,
        }
        for name, digest in sorted(references.items())
    )


def _verify_receipt(
    root: Path, envelope_hash: str, run_id: str, receipt: JsonDict
) -> None:
    if (
        receipt.get("version") != "assay-replay-verification-v1"
        or receipt.get("envelope_sha256") != envelope_hash
        or receipt.get("run_id") != run_id
        or receipt.get("silver_equal") is not True
        or receipt.get("gold_equal") is not True
        or not isinstance(receipt.get("objects"), dict)
        or not receipt["objects"]
    ):
        raise ValueError("assay_replay_verification_invalid")
    for name, digest in receipt["objects"].items():
        if (
            digest_bytes(confined_path(root / "verification", name).read_bytes())
            != digest
        ):
            raise ValueError("assay_replay_output_object_mismatch")


def project_assay_replay(
    run_root: Path,
    run_id: str,
    report: JsonDict,
    manifest: JsonDict | None,
) -> tuple[JsonDict | None, JsonDict | None]:
    """Upgrade only a verified offline proof; preserve all other strict checks."""
    items = report.get("artifacts", [])
    parents = [
        item
        for item in items
        if isinstance(item, dict) and item.get("kind") == "composite_exact_replay"
    ]
    if not parents:
        return manifest, None
    probe: JsonDict = {
        "code": "assay_offline_replay",
        "result": "fail",
        "reason": "assay_replay_evidence_invalid",
        "evidence_ref": "replay/parent.json",
    }
    try:
        if (
            len(parents) != 1
            or parents[0].get("ref") != "replay/parent.json"
            or manifest is None
        ):
            raise ValueError("assay_replay_binding_invalid")
        root = run_root / "replay"
        envelope_hash = parents[0]["sha256"]
        envelope = verify_bundle(root, envelope_hash)
        if envelope["run_id"] != run_id:
            raise ValueError("assay_replay_identity_mismatch")
        receipts = [
            item
            for item in items
            if isinstance(item, dict)
            and item.get("ref") == "replay/verification/verification.json"
        ]
        if len(receipts) != 1:
            raise ValueError("assay_replay_verification_missing")
        receipt = load_verified_json(
            root, _VERIFICATION_RECEIPT_FILE, receipts[0]["sha256"]
        )
        _verify_receipt(root, envelope_hash, run_id, receipt)
        upgraded = {
            **manifest,
            "replay_capability": "exact_replay_supported",
            "exact_replay_supported": True,
            "strict_exact_replay_supported": True,
            "input_snapshot_fingerprint": envelope["input_snapshot_fingerprint"],
            "objects": {
                **manifest.get("objects", {}),
                "input_snapshot_fingerprint": True,
            },
        }
        probe.update(result="pass", reason="assay_offline_replay_verified")
        return upgraded, probe
    except (OSError, ValueError, KeyError, TypeError):
        return manifest, probe
