"""cleanup group records for cooperative, fail-closed POSIX cleanup."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .cleanup_core import (
    BronzeRootLease,
    _CleanupConflict,
    _platform_cleanup_supported,
)
from .cleanup_group_schema import (
    _DIR_FLAGS,
    _FILE_FLAGS,
    _JOURNAL_DIR,
    _MAX_RECORD,
    _NOFOLLOW,
    _STAGE_PREFIX,
    GroupJournalConflict,
    _decode_record,
    _effective_uid,
    _exists,
    _identity,
    _record_bytes,
    _write_all,
)
from .cleanup_posix import _anchored_parent, _chain_is_stable


class GroupRecordStore:
    """cleanup group records responsibilities."""

    def __init__(self, lease: BronzeRootLease):
        # Construction also serves read-only planning; volume probes belong to apply.
        if lease.fd is None or not _platform_cleanup_supported():
            raise NotImplementedError("missing pinned POSIX Bronze root")
        self._root = lease.path
        self._root_fd = lease.fd
        self._record_witnesses: dict[str, tuple[int, int, bytes]] = {}

    @contextmanager
    def _date(self, relative: str) -> Iterator[tuple[int, list[list[int]]]]:
        target = self._root / relative / "_member"
        try:
            with _anchored_parent(
                target,
                self._root,
                self._root,
                self._root_fd,
                require_destructive_capability=False,
            ) as (
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
        except _CleanupConflict as exc:
            raise GroupJournalConflict("root or date chain changed") from exc

    def _private_dir(
        self, name: str, *, create: bool, exclusive: bool = False
    ) -> int | None:
        if create:
            try:
                os.mkdir(name, 0o700, dir_fd=self._root_fd)
            except FileExistsError:
                if exclusive:
                    raise GroupJournalConflict(
                        "unassociated stage already exists"
                    ) from None
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
        if create:
            try:
                os.fsync(self._root_fd)
            except BaseException:
                try:
                    if exclusive:
                        self._discard_created_empty_dir(name, fd)
                finally:
                    os.close(fd)
                raise
        return fd

    def _discard_created_empty_dir(self, name: str, fd: int) -> None:
        """Retire only this attempt's held, still-named empty directory."""
        named = os.stat(name, dir_fd=self._root_fd, follow_symlinks=False)
        if [named.st_dev, named.st_ino] != _identity(fd):
            raise GroupJournalConflict("new directory was substituted")
        with os.scandir(fd) as entries:
            if next(entries, None) is not None:
                raise GroupJournalConflict("new directory is not empty")
        os.rmdir(name, dir_fd=self._root_fd)
        os.fsync(self._root_fd)

    @staticmethod
    def _checked_file(parent_fd: int, name: str) -> bytes:
        return GroupRecordStore._file_witness(parent_fd, name)[2]

    @staticmethod
    def _file_witness(parent_fd: int, name: str) -> tuple[int, int, bytes]:
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
            raw = os.read(fd, _MAX_RECORD + 1)
            after = os.fstat(fd)
            if len(raw) != st.st_size or (
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ) != (st.st_size, st.st_mtime_ns, st.st_ctime_ns):
                raise GroupJournalConflict("journal changed during read")
            return st.st_dev, st.st_ino, raw
        finally:
            os.close(fd)

    def _persist_intent(
        self, operation_id: str, body: dict[str, Any]
    ) -> None:  # Any: validated JSON.
        journal_fd = self._private_dir(_JOURNAL_DIR, create=True)
        assert journal_fd is not None
        try:
            existing = self._read_intent(journal_fd, operation_id)
            if existing == body:
                # replace may have succeeded before the directory fsync failed.
                # Retry the durability barrier before returning the same intent.
                os.fsync(journal_fd)
                return
            self._reject_pending_duplicate(journal_fd, body)
            if _exists(journal_fd, f"{operation_id}.json") or _exists(
                journal_fd, f"{operation_id}.next"
            ):
                raise GroupJournalConflict("group operation ID already exists")
            self._replace_record(journal_fd, operation_id, body)
        finally:
            os.close(journal_fd)

    def _reject_pending_duplicate(
        self, journal_fd: int, body: dict[str, Any]
    ) -> None:  # Any: validated JSON.
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

    def _read_intent(
        self, journal_fd: int, operation_id: str
    ) -> dict[str, Any] | None:  # Any: validated JSON.
        try:
            witness = self._file_witness(journal_fd, f"{operation_id}.json")
            body = _decode_record(witness[2], operation_id)
            self._record_witnesses[operation_id] = witness
            return body
        except FileNotFoundError:
            if _exists(journal_fd, f"{operation_id}.next") or _exists(
                self._root_fd, f"{_STAGE_PREFIX}{operation_id}"
            ):
                raise GroupJournalConflict(
                    "stage or partial journal has no intent"
                ) from None
            self._record_witnesses.pop(operation_id, None)
            return None

    def _discard_temp(self, journal_fd: int, operation_id: str) -> None:
        temp_name = f"{operation_id}.next"
        if _exists(journal_fd, temp_name):
            raise GroupJournalConflict("unassociated journal replacement retained")

    def _replace_record(
        self,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],  # Any: validated JSON.
    ) -> None:
        self._discard_temp(journal_fd, operation_id)
        self._assert_record(journal_fd, operation_id)
        temp_name = f"{operation_id}.next"
        fd = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
            0o600,
            dir_fd=journal_fd,
        )
        try:
            raw = _record_bytes(body)
            _write_all(fd, raw)
            os.fsync(fd)
            self._assert_record(journal_fd, operation_id)
            owned = os.fstat(fd)
            named = os.stat(temp_name, dir_fd=journal_fd, follow_symlinks=False)
            if (named.st_dev, named.st_ino) != (owned.st_dev, owned.st_ino):
                raise GroupJournalConflict("journal replacement changed")
            os.replace(
                temp_name,
                f"{operation_id}.json",
                src_dir_fd=journal_fd,
                dst_dir_fd=journal_fd,
            )
            self._record_witnesses[operation_id] = (owned.st_dev, owned.st_ino, raw)
            os.fsync(journal_fd)
        except BaseException:
            # Only this invocation owns the still-open exclusive-created inode.
            # A pre-existing/torn replacement from restart is never discarded.
            try:
                named = os.stat(temp_name, dir_fd=journal_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                owned = os.fstat(fd)
                if (named.st_dev, named.st_ino) == (owned.st_dev, owned.st_ino):
                    os.unlink(temp_name, dir_fd=journal_fd)
                    os.fsync(journal_fd)
            raise
        finally:
            os.close(fd)

    def _assert_record(self, journal_fd: int, operation_id: str) -> None:
        expected = self._record_witnesses.get(operation_id)
        try:
            current = self._file_witness(journal_fd, f"{operation_id}.json")
        except FileNotFoundError:
            if expected is None:
                return
            raise GroupJournalConflict("journal disappeared") from None
        if current != expected:
            raise GroupJournalConflict("journal replaced")

    def _complete_record(
        self,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],  # Any: validated JSON.
    ) -> None:
        self._replace_record(journal_fd, operation_id, {**body, "state": "completed"})
