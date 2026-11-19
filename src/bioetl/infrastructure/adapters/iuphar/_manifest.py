"""Bounded, content-checked local JSON reads for frozen IUPHAR artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def require_sha256(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("expected a lowercase SHA-256 digest")
    return value


def decode_json(payload: bytes) -> object:
    def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    return json.loads(payload.decode("utf-8"), object_pairs_hook=unique_pairs)


def object_document(payload: bytes) -> dict[str, object]:
    value = decode_json(payload)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def checked_bytes(path: Path, expected_sha256: str) -> bytes:
    resolved = path.expanduser().resolve(strict=False)
    root = resolved.parent
    relative = resolved.relative_to(root)
    if not relative.parts or any(part in {"..", "."} for part in relative.parts):
        raise ValueError("refusing an unconfined IUPHAR artifact path")
    payload = root.joinpath(*relative.parts).read_bytes()
    if sha256(payload) != require_sha256(expected_sha256):
        raise ValueError("IUPHAR artifact digest mismatch")
    return payload


def checked_document(path: Path, expected_sha256: str) -> dict[str, object]:
    return object_document(checked_bytes(path, expected_sha256))


def referenced_path(root: Path, reference: object) -> tuple[Path, str]:
    if not isinstance(reference, Mapping):
        raise ValueError("expected an artifact reference")
    relative = reference.get("path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("artifact reference must use a relative path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError("IUPHAR artifact reference escapes its manifest directory")
    return path, require_sha256(reference.get("sha256"))


def text(document: Mapping[str, object], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing IUPHAR manifest field: {key}")
    return value


def header(
    document: Mapping[str, object], artifact: str, *, versions: tuple[int, ...] = (1,)
) -> None:
    version = document.get("schema_version")
    if (
        document.get("artifact") != artifact
        or type(version) is not int
        or version not in versions
    ):
        raise ValueError("unsupported IUPHAR artifact schema")
