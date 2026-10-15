"""POSIX journal schema for an attested Bronze cleanup group.

Validated record schema and bounded member fingerprinting for Bronze journals.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
from collections.abc import Callable
from typing import Any
from uuid import UUID

from .cleanup_core import stat_is_link_or_reparse
from .cleanup_metrics import (
    GroupJournalConflict,
    GroupJournalFailure,
    GroupRecoveryResult,
    GroupSpec,
)

_JOURNAL_DIR = ".bronze-group-journals"
_STAGE_PREFIX = ".bronze-group-stage-"
_MAX_RECORD = 16_384
_MAX_SIDECAR = 1_048_576
_SCHEMA_VERSION = 4  # Persist accounted unlinks separately from staged presence.
_LEGACY_SCHEMA_VERSION = 3
_STAGE_TAG = "user.bioetl.fs001-stage"
_ORDER = ("copy", "payload", "sidecar")
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
_FILE_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
_MEMBER_NOT_REGULAR = "group member is not a regular file"
Barrier = Callable[[str], None]

__all__ = [
    "Barrier",
    "GroupJournalConflict",
    "GroupJournalFailure",
    "GroupRecoveryResult",
    "GroupSpec",
]


def _canonical(value: dict[str, Any]) -> bytes:  # Any: validated JSON.
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def _unique_pairs(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:  # Any: validated JSON.
    result: dict[str, Any] = {}  # Any: validated JSON.
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate journal key")
        result[key] = value
    return result


def _record_bytes(body: dict[str, Any]) -> bytes:  # Any: validated JSON.
    raw = _canonical(body)
    encoded = _canonical({"body": body, "sha256": hashlib.sha256(raw).hexdigest()})
    if len(encoded) > _MAX_RECORD:
        raise GroupJournalConflict("group journal exceeds size limit")
    return encoded


def _validated_scope(body: dict[str, Any]) -> dict[str, str]:  # Any: validated JSON.
    scope = body["scope"]
    if (
        not isinstance(scope, dict)
        or set(scope)
        != {"provider", "entity", "date", "batch_id", "cutoff", "flat_structure"}
        or type(scope["flat_structure"]) is not bool
    ):
        raise ValueError("scope")
    spec = GroupSpec(**scope)
    expected_names = spec.names()
    if (
        body["relative_date"] != spec.relative_date().as_posix()
        or body["names"] != expected_names
    ):
        raise ValueError("writer path")
    return expected_names


def _validate_member_identity(identity: Any) -> None:  # Any: validated JSON.
    if not isinstance(identity, dict) or set(identity) != {
        "dev",
        "ino",
        "size",
        "sha256",
    }:
        raise ValueError("identity fields")
    if any(  # Any: validated JSON.
        type(identity[k]) is not int or identity[k] < 0 for k in ("dev", "ino", "size")
    ):
        raise ValueError("identity values")
    digest = identity["sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)  # Any: validated JSON.
    ):
        raise ValueError("identity digest")


def _validate_members(
    body: dict[str, Any], expected_names: dict[str, str]
) -> None:  # Any: validated JSON.
    members = body["members"]
    if (
        not isinstance(members, dict)
        or not {"payload", "sidecar"} <= members.keys()
        or not members.keys() <= expected_names.keys()
    ):
        raise ValueError("members")
    _validate_staged(body, members)
    for identity in members.values():
        _validate_member_identity(identity)


def _validate_member_key_list(
    value: object, members: dict[str, Any], *, label: str
) -> None:  # Any: validated JSON.
    if not isinstance(value, list):
        raise ValueError(label)
    keys = list(value)
    ok = (
        len(keys) == len(set(keys))
        and all(key in members for key in keys)  # Any: validated JSON.
        and keys == [key for key in _ORDER if key in keys]
    )
    if not ok:
        raise ValueError(label)


def _validate_staged(
    body: dict[str, Any], members: dict[str, Any]
) -> None:  # Any: validated JSON.
    _validate_member_key_list(body["staged"], members, label="staged members")
    removed = body.get("removed", [])
    _validate_member_key_list(removed, members, label="removed members")
    if any(key not in body["staged"] for key in removed):  # Any: validated JSON.
        raise ValueError("removed before staged")
    if body["state"] == "completed" and set(body["staged"]) != set(members):
        raise ValueError("incomplete completion")


def _validate_chain(body: dict[str, Any]) -> None:  # Any: validated JSON.
    chain = body["chain"]
    if not isinstance(chain, list) or not chain or chain[0] != body["root"]:
        raise ValueError("root chain")
    for item in [body["root"], *chain]:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or any(type(n) is not int or n < 0 for n in item)  # Any: validated JSON.
        ):
            raise ValueError("directory identity")


_BODY_KEYS = frozenset(
    [
        "schema",
        "operation_id",
        "state",
        "scope",
        "relative_date",
        "root",
        "chain",
        "names",
        "members",
        "staged",
        "stage",
        "removed",
    ]
)
_LEGACY_BODY_KEYS = _BODY_KEYS - {"removed"}


def _validate_record_body(
    body: dict[str, Any], operation_id: str
) -> None:  # Any: validated JSON.
    keys = set(body)
    schema = body.get("schema")
    if (
        type(schema) is not int
        or schema not in (_SCHEMA_VERSION, _LEGACY_SCHEMA_VERSION)
        or body.get("operation_id") != operation_id
        or body.get("state") not in ("prepared", "completed")
    ):
        raise ValueError("schema, operation or state")
    if schema == _LEGACY_SCHEMA_VERSION and keys == _LEGACY_BODY_KEYS:
        # Upgrade in place before any rewrite so schema-3 + removed[] never persists.
        body["removed"] = []
        body["schema"] = _SCHEMA_VERSION
    elif not (schema == _SCHEMA_VERSION and keys == _BODY_KEYS):
        raise ValueError("body keys")
    if UUID(hex=operation_id).hex != operation_id:
        raise ValueError("operation ID")
    _validate_members(body, _validated_scope(body))
    _validate_chain(body)
    _validate_stage(body)


def _validate_stage(body: dict[str, Any]) -> None:  # Any: validated JSON.
    stage = body["stage"]
    if stage is None:
        if body["staged"] or body["state"] != "prepared":
            raise ValueError("unassociated stage transition")
        return
    if (
        not isinstance(stage, dict)
        or set(stage) != {"dev", "ino", "token"}
        or any(
            type(stage[key]) is not int or stage[key] < 0 for key in ("dev", "ino")
        )  # Any: validated JSON.
        or not isinstance(stage["token"], str)
        or UUID(hex=stage["token"]).hex != stage["token"]
    ):
        raise ValueError("stage association")


def _decode_record(
    raw: bytes, operation_id: str
) -> dict[str, Any]:  # Any: validated JSON.
    """Reject torn, ambiguous, foreign and non-canonical records before I/O."""
    try:
        if not raw or len(raw) > _MAX_RECORD:
            raise ValueError("journal size")
        envelope = json.loads(raw, object_pairs_hook=_unique_pairs)
        if not isinstance(envelope, dict) or set(envelope) != {"body", "sha256"}:
            raise ValueError("envelope keys")
        body = envelope["body"]
        if (
            not isinstance(body, dict)
            or envelope["sha256"] != hashlib.sha256(_canonical(body)).hexdigest()
        ):
            raise ValueError("checksum")
        _validate_record_body(body, operation_id)
        return body
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise GroupJournalConflict("invalid or foreign Bronze group journal") from exc


def _identity(fd: int) -> list[int]:
    st = os.fstat(fd)
    return [st.st_dev, st.st_ino]


def _effective_uid() -> int:
    get_uid = getattr(os, "geteuid", None)
    if get_uid is None:
        raise NotImplementedError("POSIX uid validation unavailable")
    return int(get_uid())


def _require_operation_id(operation_id: str) -> None:
    try:
        if UUID(hex=operation_id).hex != operation_id:
            raise ValueError("non-canonical operation ID")
    except ValueError as exc:
        raise GroupJournalConflict("invalid operation ID") from exc


def _open_regular_member(parent_fd: int, name: str) -> int:
    """Reject a link before open so ELOOP is a conflict, not a failed read."""
    named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat_is_link_or_reparse(named) or not stat.S_ISREG(named.st_mode):
        raise GroupJournalConflict(_MEMBER_NOT_REGULAR)
    try:
        return os.open(name, _FILE_FLAGS, dir_fd=parent_fd)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise GroupJournalConflict(_MEMBER_NOT_REGULAR) from exc
        raise


def _fingerprint(parent_fd: int, name: str) -> dict[str, Any]:  # Any: validated JSON.
    fd = _open_regular_member(parent_fd, name)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise GroupJournalConflict(_MEMBER_NOT_REGULAR)
        digest = hashlib.sha256()
        size = 0
        while chunk := os.read(fd, 1_048_576):
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(fd)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) or size != before.st_size:
            raise GroupJournalConflict("group member changed while read")
        return {
            "dev": before.st_dev,
            "ino": before.st_ino,
            "size": size,
            "sha256": digest.hexdigest(),
        }
    finally:
        os.close(fd)


def _exists(parent_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _write_all(fd: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        wrote = os.write(fd, raw[offset:])
        if wrote <= 0:
            raise OSError("short journal write")
        offset += wrote


def _validate_association(
    metadata: dict[str, Any],
    spec: GroupSpec,
    members: dict[str, dict[str, Any]],  # Any: validated JSON.
) -> None:
    """Require writer-produced content association before adopting a group.

    Legacy lineage labels or matching filenames alone do not attest ownership.
    Fingerprints in the durable intent subsequently pin these exact objects.
    """
    association = metadata.get("cleanup_association")
    if (
        any(  # Any: validated JSON.
            metadata.get(key) != value
            for key, value in (
                ("provider", spec.provider),
                ("entity", spec.entity),
                ("batch_id", spec.batch_id),
            )
        )
        or not isinstance(association, dict)
        or set(association) != {"schema", "payload_sha256", "copy_sha256"}
        or type(association["schema"]) is not int
        or association["schema"] != 1
        or not _optional_copy_digest_valid(association["copy_sha256"])
        or association["payload_sha256"] != members["payload"]["sha256"]
        or (
            "copy" in members
            and association["copy_sha256"] != members["copy"]["sha256"]
        )
    ):
        raise GroupJournalConflict("unassociated Bronze group content")


def _optional_copy_digest_valid(value: Any) -> bool:  # Any: validated JSON.
    return value is None or (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )
