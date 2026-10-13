"""Opt-in POSIX journal for an already validated Bronze cleanup group.

No production cleanup caller imports this module. Recovery requires an explicit
operation ID and the same cooperative exclusive root lock as Bronze cleanup.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .cleanup_core import (
    BronzeRootLease,
    destructive_cleanup_supported,
    valid_bronze_scope_name,
)
from .cleanup_posix import _anchored_parent, _chain_is_stable
from .cleanup_support import bronze_tree_lock, date_dir_name_is_older, is_owned_artifact
from .validation_mixin import BronzeWriterValidationMixin

_JOURNAL_DIR = ".bronze-group-journals"
_STAGE_PREFIX = ".bronze-group-stage-"
_MAX_RECORD = 16_384
_MAX_SIDECAR = 1_048_576
_ORDER = ("copy", "payload", "sidecar")
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
_FILE_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
Barrier = Callable[[str], None]


class GroupJournalConflict(OSError):
    """The journal or a group member cannot be proven to be the original."""

    operation_id: str | None = None
    removed: int = 0
    possibly_unlinked: int = 0
    phase: str = "read"


class GroupJournalFailure(OSError):
    """An I/O barrier failed after a known number of successful unlinks."""

    def __init__(
        self, operation_id: str, removed: int, phase: str, possibly_unlinked: int
    ):
        super().__init__(
            f"group {operation_id} failed at {phase}; durably_removed={removed}; possibly_unlinked={possibly_unlinked}"
        )
        self.operation_id = operation_id
        self.removed = removed
        self.phase = phase
        self.possibly_unlinked = possibly_unlinked


@dataclass(slots=True)
class _RecoveryProgress:
    removed: int = 0
    possibly_unlinked: int = 0
    phase: str = "read"


@dataclass(frozen=True, slots=True)
class GroupSpec:
    """Exact writer scope and calendar eligibility for one complete group."""

    provider: str
    entity: str
    date: str
    batch_id: str
    cutoff: str
    flat_structure: bool = False

    def names(self) -> dict[str, str]:
        if not all(valid_bronze_scope_name(x) for x in (self.provider, self.entity)):
            raise ValueError("invalid Bronze provider/entity")
        for value in (self.date, self.cutoff):
            try:
                if datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") != value:
                    raise ValueError("non-canonical date")
            except ValueError as exc:
                raise ValueError("invalid Bronze date/cutoff") from exc
        if not date_dir_name_is_older(self.date, self.cutoff):
            raise ValueError("group is not older than cutoff")
        try:
            if str(UUID(self.batch_id)) != self.batch_id:
                raise ValueError("non-canonical batch ID")
        except ValueError as exc:
            raise ValueError("invalid batch ID") from exc
        payload = f"batch_{self.date}_{self.batch_id}.jsonl.zst"
        if not is_owned_artifact(payload, date_name=self.date):
            raise ValueError("group does not match writer naming")
        return {
            "copy": payload.removesuffix(".zst"),
            "payload": payload,
            "sidecar": f"{payload}.meta.json",
        }

    def relative_date(self) -> Path:
        if type(self.flat_structure) is not bool:
            raise ValueError("invalid Bronze layout flag")
        payload = self.names()["payload"]
        resolver = BronzeWriterValidationMixin()
        resolver._flat_structure = self.flat_structure
        return Path(
            resolver._resolve_bronze_path(
                self.provider, self.entity, self.date, payload
            )
        ).parent


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate journal key")
        result[key] = value
    return result


def _record_bytes(body: dict[str, Any]) -> bytes:
    raw = _canonical(body)
    encoded = _canonical({"body": body, "sha256": hashlib.sha256(raw).hexdigest()})
    if len(encoded) > _MAX_RECORD:
        raise GroupJournalConflict("group journal exceeds size limit")
    return encoded


def _validated_scope(body: dict[str, Any]) -> dict[str, str]:
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


def _validate_member_identity(identity: Any) -> None:
    if not isinstance(identity, dict) or set(identity) != {
        "dev",
        "ino",
        "size",
        "sha256",
    }:
        raise ValueError("identity fields")
    if any(
        type(identity[k]) is not int or identity[k] < 0 for k in ("dev", "ino", "size")
    ):
        raise ValueError("identity values")
    digest = identity["sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        raise ValueError("identity digest")


def _validate_members(body: dict[str, Any], expected_names: dict[str, str]) -> None:
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


def _validate_staged(body: dict[str, Any], members: dict[str, Any]) -> None:
    staged = body["staged"]
    if (
        not isinstance(staged, list)
        or len(staged) != len(set(staged))
        or any(key not in members for key in staged)
        or staged != [key for key in _ORDER if key in staged]
    ):
        raise ValueError("staged members")
    if body["state"] == "completed" and set(staged) != set(members):
        raise ValueError("incomplete completion")


def _validate_chain(body: dict[str, Any]) -> None:
    chain = body["chain"]
    if not isinstance(chain, list) or not chain or chain[0] != body["root"]:
        raise ValueError("root chain")
    for item in [body["root"], *chain]:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or any(type(n) is not int or n < 0 for n in item)
        ):
            raise ValueError("directory identity")


def _validate_record_body(body: dict[str, Any], operation_id: str) -> None:
    if set(body) != {
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
    }:
        raise ValueError("body keys")
    if (
        body["schema"] != 1
        or body["operation_id"] != operation_id
        or body["state"] not in ("prepared", "completed")
    ):
        raise ValueError("schema, operation or state")
    if UUID(hex=operation_id).hex != operation_id:
        raise ValueError("operation ID")
    _validate_members(body, _validated_scope(body))
    _validate_chain(body)


def _decode_record(raw: bytes, operation_id: str) -> dict[str, Any]:
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


def _fingerprint(parent_fd: int, name: str) -> dict[str, Any]:
    fd = os.open(name, _FILE_FLAGS, dir_fd=parent_fd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise GroupJournalConflict("group member is not a regular file")
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


@contextmanager
def open_group_journal(root: Path) -> Iterator[GroupJournal]:
    """Hold the production cooperative exclusive lock for explicit operations."""
    if not destructive_cleanup_supported():
        raise NotImplementedError(
            "durable Bronze group apply requires POSIX pinned handles"
        )
    with bronze_tree_lock(root, exclusive=True) as lease:
        yield GroupJournal(lease)


class GroupJournal:
    """Explicit begin/recover API; never enumerated by production cleanup."""

    def __init__(self, lease: BronzeRootLease):
        if lease.fd is None or not destructive_cleanup_supported():
            raise NotImplementedError("missing pinned POSIX Bronze root")
        self._root = lease.path
        self._root_fd = lease.fd

    @contextmanager
    def _date(self, relative: str) -> Iterator[tuple[int, list[list[int]]]]:
        target = self._root / relative / "_member"
        with _anchored_parent(target, self._root, self._root, self._root_fd) as (
            root_fd,
            date_fd,
            _name,
            chain,
        ):
            if not _chain_is_stable(root_fd, self._root, chain):
                raise GroupJournalConflict("date chain changed")
            yield (
                date_fd,
                [
                    _identity(root_fd),
                    *(_identity(child) for _parent, child, _part in chain),
                ],
            )

    def _private_dir(self, name: str, *, create: bool) -> int | None:
        if create:
            try:
                os.mkdir(name, 0o700, dir_fd=self._root_fd)
                os.fsync(self._root_fd)
            except FileExistsError:
                pass
        try:
            fd = os.open(name, _DIR_FLAGS, dir_fd=self._root_fd)
        except FileNotFoundError:
            return None
        st = os.fstat(fd)
        if (
            not stat.S_ISDIR(st.st_mode)
            or st.st_uid != _effective_uid()
            or stat.S_IMODE(st.st_mode) & 0o077
        ):
            os.close(fd)
            raise GroupJournalConflict("untrusted group journal/stage directory")
        return fd

    @staticmethod
    def _checked_file(parent_fd: int, name: str) -> bytes:
        fd = os.open(name, _FILE_FLAGS, dir_fd=parent_fd)
        try:
            st = os.fstat(fd)
            if (
                not stat.S_ISREG(st.st_mode)
                or st.st_uid != _effective_uid()
                or stat.S_IMODE(st.st_mode) & 0o077
                or st.st_nlink != 1
                or st.st_size > _MAX_RECORD
            ):
                raise GroupJournalConflict("untrusted group journal file")
            return os.read(fd, _MAX_RECORD + 1)
        finally:
            os.close(fd)

    def begin(self, spec: GroupSpec, hook: Barrier | None = None) -> str:
        """Durably attest a complete writer group before any member removal."""
        names = spec.names()  # validate before date traversal
        relative = spec.relative_date().as_posix()
        members, chain = self._snapshot_group(spec, names, relative)
        operation_id = uuid4().hex
        body = {
            "schema": 1,
            "operation_id": operation_id,
            "state": "prepared",
            "scope": {
                "provider": spec.provider,
                "entity": spec.entity,
                "date": spec.date,
                "batch_id": spec.batch_id,
                "cutoff": spec.cutoff,
                "flat_structure": spec.flat_structure,
            },
            "relative_date": relative,
            "root": chain[0],
            "chain": chain,
            "names": names,
            "members": members,
            "staged": [],
        }
        if hook:
            hook("before_intent_create")
        self._persist_intent(operation_id, body)
        if hook:
            hook("after_intent_fsync")
        return operation_id

    def _snapshot_group(
        self, spec: GroupSpec, names: dict[str, str], relative: str
    ) -> tuple[dict[str, dict[str, Any]], list[list[int]]]:
        with self._date(relative) as (date_fd, chain):
            members = {
                key: _fingerprint(date_fd, names[key]) for key in ("payload", "sidecar")
            }
            if _exists(date_fd, names["copy"]):
                members["copy"] = _fingerprint(date_fd, names["copy"])
            self._validate_sidecar(date_fd, names["sidecar"], spec)
            if chain != self._current_chain(relative):
                raise GroupJournalConflict("date chain changed before intent")
        return members, chain

    @staticmethod
    def _validate_sidecar(date_fd: int, name: str, spec: GroupSpec) -> None:
        sidecar_fd = os.open(name, _FILE_FLAGS, dir_fd=date_fd)
        try:
            raw = os.read(sidecar_fd, _MAX_SIDECAR + 1)
        finally:
            os.close(sidecar_fd)
        try:
            meta = json.loads(raw, object_pairs_hook=_unique_pairs)
            if (
                len(raw) > _MAX_SIDECAR
                or not isinstance(meta, dict)
                or any(
                    meta.get(k) != v
                    for k, v in (
                        ("provider", spec.provider),
                        ("entity", spec.entity),
                        ("batch_id", spec.batch_id),
                    )
                )
            ):
                raise ValueError("sidecar does not identify this writer group")
        except (ValueError, TypeError) as exc:
            raise GroupJournalConflict("unassociated Bronze sidecar") from exc

    def _persist_intent(self, operation_id: str, body: dict[str, Any]) -> None:
        raw_record = _record_bytes(body)
        journal_fd = self._private_dir(_JOURNAL_DIR, create=True)
        assert journal_fd is not None
        try:
            self._reject_pending_duplicate(journal_fd, body)
            fd = os.open(
                f"{operation_id}.json",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
                0o600,
                dir_fd=journal_fd,
            )
            try:
                _write_all(fd, raw_record)
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(journal_fd)
        finally:
            os.close(journal_fd)

    def _reject_pending_duplicate(self, journal_fd: int, body: dict[str, Any]) -> None:
        for existing in os.listdir(journal_fd):
            if len(existing) != 37 or not existing.endswith(".json"):
                raise GroupJournalConflict("unknown pending group journal entry")
            existing_id = existing.removesuffix(".json")
            pending = _decode_record(
                self._checked_file(journal_fd, existing), existing_id
            )
            if pending["root"] != _identity(self._root_fd):
                raise GroupJournalConflict("foreign pending group journal")
            if (
                pending["relative_date"] == body["relative_date"]
                and pending["names"] == body["names"]
            ):
                raise GroupJournalConflict("group already has a pending intent")

    def recover(self, operation_id: str, hook: Barrier | None = None) -> int:
        """Resume only a previously attested operation, never infer an orphan."""
        _require_operation_id(operation_id)
        journal_fd = self._journal_dir_for_recovery(operation_id)
        if journal_fd is None:
            return 0
        progress = _RecoveryProgress()
        try:
            body = self._read_intent(journal_fd, operation_id)
            if body is None:
                return 0
            if body["root"] != _identity(self._root_fd):
                raise GroupJournalConflict("journal belongs to another root")
            self._discard_temp(journal_fd, operation_id)
            self._recover_body(journal_fd, operation_id, body, hook, progress)
            return progress.removed
        except GroupJournalConflict as exc:
            exc.operation_id = operation_id
            exc.removed = progress.removed
            exc.possibly_unlinked = progress.possibly_unlinked
            exc.phase = progress.phase
            raise
        except OSError as exc:
            raise GroupJournalFailure(
                operation_id,
                progress.removed,
                progress.phase,
                progress.possibly_unlinked,
            ) from exc
        finally:
            os.close(journal_fd)

    def _journal_dir_for_recovery(self, operation_id: str) -> int | None:
        journal_fd = self._private_dir(_JOURNAL_DIR, create=False)
        if journal_fd is None and _exists(
            self._root_fd, f"{_STAGE_PREFIX}{operation_id}"
        ):
            raise GroupJournalConflict("stage exists without group journal directory")
        return journal_fd

    def _read_intent(self, journal_fd: int, operation_id: str) -> dict[str, Any] | None:
        try:
            return _decode_record(
                self._checked_file(journal_fd, f"{operation_id}.json"), operation_id
            )
        except FileNotFoundError:
            if _exists(journal_fd, f"{operation_id}.next") or _exists(
                self._root_fd, f"{_STAGE_PREFIX}{operation_id}"
            ):
                raise GroupJournalConflict(
                    "stage or partial journal has no intent"
                ) from None
            return None

    def _recover_body(
        self,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],
        hook: Barrier | None,
        progress: _RecoveryProgress,
    ) -> None:
        relative = body["relative_date"]
        with self._date(relative) as (date_fd, chain):
            if chain != body["chain"]:
                raise GroupJournalConflict("date or ancestor replaced")
            stage_name = f"{_STAGE_PREFIX}{operation_id}"
            stage_fd = self._private_dir(stage_name, create=body["state"] == "prepared")
            stage_identity = _identity(stage_fd) if stage_fd is not None else None
            try:
                if body["state"] == "prepared":
                    assert stage_fd is not None
                    self._apply_group(
                        date_fd,
                        stage_fd,
                        journal_fd,
                        operation_id,
                        body,
                        relative,
                        chain,
                        hook,
                        progress,
                    )
                self._record_completion(
                    date_fd,
                    stage_fd,
                    journal_fd,
                    operation_id,
                    body,
                    relative,
                    chain,
                    hook,
                    progress,
                )
            finally:
                if stage_fd is not None:
                    os.close(stage_fd)
            self._finish_operation(
                journal_fd, operation_id, stage_name, stage_identity, hook, progress
            )

    def _apply_group(
        self,
        date_fd: int,
        stage_fd: int,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],
        relative: str,
        chain: list[list[int]],
        hook: Barrier | None,
        progress: _RecoveryProgress,
    ) -> None:
        self._preflight_group(date_fd, stage_fd, body)
        for key in _ORDER:
            if key in body["members"]:
                self._recover_member(
                    date_fd,
                    stage_fd,
                    journal_fd,
                    operation_id,
                    body,
                    key,
                    relative,
                    chain,
                    hook,
                    progress,
                )

    def _record_completion(
        self,
        date_fd: int,
        stage_fd: int | None,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],
        relative: str,
        chain: list[list[int]],
        hook: Barrier | None,
        progress: _RecoveryProgress,
    ) -> None:
        progress.phase = "completion"
        if hook:
            hook("before_completion")
        if chain != self._current_chain(relative) or any(
            _exists(date_fd, body["names"][key])
            or (stage_fd is not None and _exists(stage_fd, key))
            for key in body["members"]
        ):
            raise GroupJournalConflict("group is not durably absent")
        if body["state"] == "prepared":
            self._complete_record(journal_fd, operation_id, body)
        if hook:
            hook("after_completion_fsync")

    def _finish_operation(
        self,
        journal_fd: int,
        operation_id: str,
        stage_name: str,
        stage_identity: list[int] | None,
        hook: Barrier | None,
        progress: _RecoveryProgress,
    ) -> None:
        progress.phase = "finalize"
        if _exists(self._root_fd, stage_name):
            named = os.stat(stage_name, dir_fd=self._root_fd, follow_symlinks=False)
            if stage_identity is None or [named.st_dev, named.st_ino] != stage_identity:
                raise GroupJournalConflict("group stage directory replaced")
            os.rmdir(stage_name, dir_fd=self._root_fd)
            os.fsync(self._root_fd)
        if hook:
            hook("before_journal_unlink")
        os.unlink(f"{operation_id}.json", dir_fd=journal_fd)
        os.fsync(journal_fd)
        if hook:
            hook("after_journal_unlink")

    def _current_chain(self, relative: str) -> list[list[int]]:
        with self._date(relative) as (_fd, chain):
            return chain

    def _preflight_group(
        self, date_fd: int, stage_fd: int, body: dict[str, Any]
    ) -> None:
        """Reject ambiguous later members before deleting any earlier member."""
        if set(os.listdir(stage_fd)) - set(body["members"]):
            raise GroupJournalConflict("unknown content in group stage")
        for key in body["members"]:
            self._verify_member_state(date_fd, stage_fd, body, key)

    @staticmethod
    def _verify_member_state(
        date_fd: int, stage_fd: int, body: dict[str, Any], key: str
    ) -> None:
        name = body["names"][key]
        source = _exists(date_fd, name)
        staged = _exists(stage_fd, key)
        if source and staged:
            raise GroupJournalConflict(f"ambiguous duplicate {key}")
        if not source and not staged and key not in body["staged"]:
            raise GroupJournalConflict(f"unexplained absence of {key}")
        if source and _fingerprint(date_fd, name) != body["members"][key]:
            raise GroupJournalConflict(f"replaced {key}")
        if staged and _fingerprint(stage_fd, key) != body["members"][key]:
            raise GroupJournalConflict(f"replaced staged {key}")

    def _recover_member(
        self,
        date_fd: int,
        stage_fd: int,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],
        key: str,
        relative: str,
        chain: list[list[int]],
        hook: Barrier | None,
        progress: _RecoveryProgress,
    ) -> None:
        progress.phase = f"{key}_identity"
        self._verify_member_state(date_fd, stage_fd, body, key)
        if _exists(date_fd, body["names"][key]):
            progress.phase = f"{key}_stage"
            self._stage_member(date_fd, stage_fd, body, key, relative, chain, hook)
        if not _exists(stage_fd, key):
            return
        self._unlink_staged(
            stage_fd,
            journal_fd,
            operation_id,
            body,
            key,
            relative,
            chain,
            hook,
            progress,
        )

    def _stage_member(
        self,
        date_fd: int,
        stage_fd: int,
        body: dict[str, Any],
        key: str,
        relative: str,
        chain: list[list[int]],
        hook: Barrier | None,
    ) -> None:
        if hook:
            hook(f"before_{key}_stage")
        if chain != self._current_chain(relative):
            raise GroupJournalConflict("date chain changed")
        if _fingerprint(date_fd, body["names"][key]) != body["members"][key]:
            raise GroupJournalConflict(f"replaced {key} before stage")
        os.rename(body["names"][key], key, src_dir_fd=date_fd, dst_dir_fd=stage_fd)
        if _fingerprint(stage_fd, key) != body["members"][key]:
            raise GroupJournalConflict(f"staged {key} changed")
        os.fsync(date_fd)
        os.fsync(stage_fd)
        if hook:
            hook(f"after_{key}_stage")

    def _unlink_staged(
        self,
        stage_fd: int,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],
        key: str,
        relative: str,
        chain: list[list[int]],
        hook: Barrier | None,
        progress: _RecoveryProgress,
    ) -> None:
        if _fingerprint(stage_fd, key) != body["members"][key]:
            raise GroupJournalConflict(f"replaced staged {key}")
        if key not in body["staged"]:
            progress.phase = f"{key}_staged_record"
            body["staged"] = [
                member for member in _ORDER if member in (*body["staged"], key)
            ]
            self._replace_record(journal_fd, operation_id, body)
            if hook:
                hook(f"after_{key}_staged_record")
        if hook:
            hook(f"before_{key}_unlink")
        progress.phase = f"{key}_unlink"
        if chain != self._current_chain(relative):
            raise GroupJournalConflict("date chain changed")
        if _fingerprint(stage_fd, key) != body["members"][key]:
            raise GroupJournalConflict(f"replaced staged {key} before unlink")
        os.unlink(key, dir_fd=stage_fd)
        progress.possibly_unlinked += 1
        os.fsync(stage_fd)
        progress.possibly_unlinked -= 1
        progress.removed += 1
        if hook:
            hook(f"after_{key}_unlink")

    def _discard_temp(self, journal_fd: int, operation_id: str) -> None:
        temp_name = f"{operation_id}.next"
        if _exists(journal_fd, temp_name):
            # The final record remains the durable witness. A torn replacement
            # is never trusted as intent and is removed only from this private dir.
            self._checked_file(journal_fd, temp_name)
            os.unlink(temp_name, dir_fd=journal_fd)
            os.fsync(journal_fd)

    def _replace_record(
        self, journal_fd: int, operation_id: str, body: dict[str, Any]
    ) -> None:
        self._discard_temp(journal_fd, operation_id)
        temp_name = f"{operation_id}.next"
        fd = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
            0o600,
            dir_fd=journal_fd,
        )
        try:
            _write_all(fd, _record_bytes(body))
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(
            temp_name,
            f"{operation_id}.json",
            src_dir_fd=journal_fd,
            dst_dir_fd=journal_fd,
        )
        os.fsync(journal_fd)

    def _complete_record(
        self, journal_fd: int, operation_id: str, body: dict[str, Any]
    ) -> None:
        self._replace_record(journal_fd, operation_id, {**body, "state": "completed"})
