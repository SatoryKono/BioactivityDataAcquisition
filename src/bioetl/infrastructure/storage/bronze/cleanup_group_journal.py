"""cleanup group journal for cooperative, fail-closed POSIX cleanup."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .cleanup_core import (
    destructive_cleanup_supported,
)
from .cleanup_group_recovery import GroupRecoveryCoordinator
from .cleanup_group_schema import (
    _DIR_FLAGS,
    _FILE_FLAGS,
    _JOURNAL_DIR,
    _MAX_SIDECAR,
    _SCHEMA_VERSION,
    _STAGE_PREFIX,
    _STAGE_TAG,
    Barrier,
    GroupJournalConflict,
    GroupJournalFailure,
    GroupRecoveryResult,
    GroupSpec,
    _canonical,
    _decode_record,
    _exists,
    _fingerprint,
    _identity,
    _record_bytes,
    _require_operation_id,
    _unique_pairs,
    _validate_association,
)
from .cleanup_support import bronze_tree_lock

__all__ = [
    "_DIR_FLAGS",
    "_STAGE_TAG",
    "GroupJournal",
    "GroupJournalConflict",
    "GroupJournalFailure",
    "GroupRecoveryResult",
    "GroupSpec",
    "_decode_record",
    "_record_bytes",
    "open_group_journal",
]


@contextmanager
def open_group_journal(root: Path) -> Iterator[GroupJournal]:
    """Hold the production cooperative exclusive lock for explicit operations."""
    if not destructive_cleanup_supported():
        raise NotImplementedError(
            "durable Bronze group apply requires POSIX pinned handles"
        )
    with bronze_tree_lock(root, exclusive=True, allow_group_recovery=True) as lease:
        yield GroupJournal(lease)


class GroupJournal(GroupRecoveryCoordinator):
    """cleanup group journal responsibilities."""

    def begin(
        self,
        spec: GroupSpec,
        hook: Barrier | None = None,
        *,
        expected_members: dict[str, os.stat_result] | None = None,
        expected_date: os.stat_result | None = None,
    ) -> str:
        """Durably attest a complete writer group before any member removal."""
        names = spec.names()  # validate before date traversal
        relative = spec.relative_date().as_posix()
        members, chain = self._snapshot_group(spec, names, relative)
        if expected_members is not None:
            self._check_planned_group(
                relative, names, members, expected_members, expected_date
            )
        operation_id = hashlib.sha256(
            _canonical(
                {"root": chain[0], "chain": chain, "names": names, "members": members}
            )
        ).hexdigest()[:32]
        body = {
            "schema": _SCHEMA_VERSION,
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
            "stage": None,
        }
        if hook:
            hook("before_intent_create")
        self._persist_intent(operation_id, body)
        if hook:
            hook("after_intent_fsync")
        return operation_id

    def _check_planned_group(
        self,
        relative: str,
        names: dict[str, str],
        members: dict[str, dict[str, Any]],  # Any: validated journal member JSON.
        expected: dict[str, os.stat_result],
        expected_date: os.stat_result | None,
    ) -> None:
        """Do not adopt objects substituted since the public cleanup plan."""
        if {names[key] for key in members} != set(expected):
            raise GroupJournalConflict("planned group membership changed")
        with self._date(relative) as (fd, _chain):
            if expected_date is None or _identity(fd) != [
                expected_date.st_dev,
                expected_date.st_ino,
            ]:
                raise GroupJournalConflict("planned date directory changed")
            for key, member in members.items():
                planned = expected[names[key]]
                current = os.stat(names[key], dir_fd=fd, follow_symlinks=False)
                fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
                if any(getattr(current, f) != getattr(planned, f) for f in fields):
                    raise GroupJournalConflict("planned group member changed")
                if (member["dev"], member["ino"], member["size"]) != (
                    planned.st_dev,
                    planned.st_ino,
                    planned.st_size,
                ):
                    raise GroupJournalConflict("attested group differs from plan")

    def pending(self) -> list[tuple[str, GroupSpec, int, int]]:
        """Read only owned intents and count their still-present members."""
        fd = self._private_dir(_JOURNAL_DIR, create=False)
        operations: list[tuple[str, GroupSpec, int, int]] = []
        try:
            for name in self._directory_names(fd) if fd is not None else ():
                assert fd is not None
                if len(name) != 37 or not name.endswith(".json"):
                    raise GroupJournalConflict("unknown pending journal entry")
                operation_id = name.removesuffix(".json")
                _require_operation_id(operation_id)
                body = self._read_intent(fd, operation_id)
                if body is None or body["root"] != _identity(self._root_fd):
                    raise GroupJournalConflict("pending journal changed or is foreign")
                count, size = self._pending_size(body)
                operations.append(
                    (operation_id, GroupSpec(**body["scope"]), count, size)
                )
        finally:
            if fd is not None:
                os.close(fd)
        ids = {operation[0] for operation in operations}
        if any(
            name.startswith(_STAGE_PREFIX)
            and name.removeprefix(_STAGE_PREFIX) not in ids
            for name in self._directory_names(self._root_fd)
        ):
            raise GroupJournalConflict("group stage has no owned intent")
        return operations

    @staticmethod
    def _directory_names(fd: int) -> list[str]:
        with os.scandir(fd) as entries:
            return sorted(entry.name for entry in entries)

    def _pending_size(
        self,
        body: dict[str, Any],  # Any: validated journal record JSON.
    ) -> tuple[int, int]:
        """Exclude previously removed members from this call's plan counters."""
        stage = self._private_dir(
            f"{_STAGE_PREFIX}{body['operation_id']}", create=False
        )
        try:
            if stage is not None:
                if body["stage"] is None:
                    raise GroupJournalConflict("unassociated pending stage")
                self._check_stage(stage, body["stage"])
            with self._date(body["relative_date"]) as (date, chain):
                if chain != body["chain"]:
                    raise GroupJournalConflict("pending date chain changed")
                remaining = [
                    member
                    for key, member in body["members"].items()
                    if _exists(date, body["names"][key])
                    or (stage is not None and _exists(stage, key))
                ]
                return len(remaining), sum(member["size"] for member in remaining)
        finally:
            if stage is not None:
                os.close(stage)

    def _snapshot_group(
        self, spec: GroupSpec, names: dict[str, str], relative: str
    ) -> tuple[dict[str, dict[str, Any]], list[list[int]]]:  # Any: validated JSON.
        with self._date(relative) as (date_fd, chain):
            members = {
                key: _fingerprint(date_fd, names[key]) for key in ("payload", "sidecar")
            }
            if _exists(date_fd, names["copy"]):
                members["copy"] = _fingerprint(date_fd, names["copy"])
            self._validate_sidecar(date_fd, names["sidecar"], spec, members)
            if any(
                _fingerprint(date_fd, names[key]) != identity
                for key, identity in members.items()
            ):
                raise GroupJournalConflict(
                    "group changed during association validation"
                )
            if chain != self._current_chain(relative):
                raise GroupJournalConflict("date chain changed before intent")
        return members, chain

    @staticmethod
    def _validate_sidecar(
        date_fd: int,
        name: str,
        spec: GroupSpec,
        members: dict[str, dict[str, Any]],  # Any: validated JSON.
    ) -> None:
        sidecar_fd = os.open(name, _FILE_FLAGS, dir_fd=date_fd)
        try:
            raw = os.read(sidecar_fd, _MAX_SIDECAR + 1)
        finally:
            os.close(sidecar_fd)
        try:
            meta = json.loads(raw, object_pairs_hook=_unique_pairs)
            if len(raw) > _MAX_SIDECAR or not isinstance(meta, dict):
                raise ValueError("sidecar does not identify this writer group")
            _validate_association(meta, spec, members)
        except (ValueError, TypeError) as exc:
            raise GroupJournalConflict("unassociated Bronze sidecar") from exc

    def recover(self, operation_id: str, hook: Barrier | None = None) -> int:
        """Resume only a previously attested operation, never infer an orphan."""
        return self.recover_with_result(operation_id, hook).removed

    def recover_with_result(
        self, operation_id: str, hook: Barrier | None = None
    ) -> GroupRecoveryResult:
        """Return exact bytes for this call, including a retry's remaining members."""
        _require_operation_id(operation_id)
        progress = GroupRecoveryResult()
        journal_fd = self._journal_dir_for_recovery(operation_id)
        if journal_fd is None:
            return progress
        try:
            body = self._read_intent(journal_fd, operation_id)
            if body is None:
                # A previous unlink can be visible even though its fsync failed.
                os.fsync(journal_fd)
                return progress
            if body["root"] != _identity(self._root_fd):
                raise GroupJournalConflict("journal belongs to another root")
            self._discard_temp(journal_fd, operation_id)
            self._recover_body(journal_fd, operation_id, body, hook, progress)
            return progress
        except GroupJournalConflict as exc:
            exc.operation_id = operation_id
            exc.removed = progress.removed
            exc.possibly_unlinked = progress.possibly_unlinked
            exc.removed_bytes = progress.removed_bytes
            exc.possibly_unlinked_bytes = progress.possibly_unlinked_bytes
            exc.phase = progress.phase
            raise
        except OSError as exc:
            raise GroupJournalFailure(
                operation_id,
                progress.removed,
                progress.phase,
                progress.possibly_unlinked,
                progress.removed_bytes,
                progress.possibly_unlinked_bytes,
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
