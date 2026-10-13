"""cleanup group members for cooperative, fail-closed POSIX cleanup."""

from __future__ import annotations

import errno
import os
import stat
from typing import Any

from .cleanup_group_records import GroupRecordStore
from .cleanup_group_schema import (
    _ORDER,
    _STAGE_PREFIX,
    _STAGE_TAG,
    Barrier,
    GroupJournalConflict,
    GroupRecoveryResult,
    _exists,
    _fingerprint,
    _identity,
)


class GroupMemberRecovery(GroupRecordStore):
    """cleanup group members responsibilities."""

    @staticmethod
    def _check_stage(fd: int, expected: dict[str, Any]) -> None:  # Any: validated JSON.
        getter = os.__dict__.get("getxattr")
        if getter is None:
            raise OSError(errno.ENOTSUP, "directory xattrs unavailable")
        try:
            token = getter(fd, _STAGE_TAG)
        except OSError as exc:
            if exc.errno in (errno.ENODATA, getattr(errno, "ENOATTR", errno.ENODATA)):
                raise GroupJournalConflict("stage association is missing") from exc
            raise
        if (
            _identity(fd) != [expected["dev"], expected["ino"]]
            or token != expected["token"].encode()
        ):
            raise GroupJournalConflict("stage object replaced")

    def _assert_stage_named(
        self, stage_fd: int, body: dict[str, Any]
    ) -> None:  # Any: validated JSON.
        """Do not act through a stage handle moved outside the leased namespace."""
        expected = body["stage"]
        self._check_stage(stage_fd, expected)
        try:
            named = os.stat(
                f"{_STAGE_PREFIX}{body['operation_id']}",
                dir_fd=self._root_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError as exc:
            raise GroupJournalConflict("stage disappeared") from exc
        if not stat.S_ISDIR(named.st_mode) or [named.st_dev, named.st_ino] != [
            expected["dev"],
            expected["ino"],
        ]:
            raise GroupJournalConflict("stage moved or replaced")

    def _current_chain(self, relative: str) -> list[list[int]]:
        with self._date(relative) as (_fd, chain):
            return chain

    def _preflight_group(
        self,
        date_fd: int,
        stage_fd: int,
        body: dict[str, Any],  # Any: validated JSON.
    ) -> None:
        """Reject ambiguous later members before deleting any earlier member."""
        if "copy" not in body["members"] and _exists(date_fd, body["names"]["copy"]):
            raise GroupJournalConflict("unattested group copy appeared")
        if set(os.listdir(stage_fd)) - set(body["members"]):
            raise GroupJournalConflict("unknown content in group stage")
        for key in body["members"]:
            self._verify_member_state(date_fd, stage_fd, body, key)

    @staticmethod
    def _verify_member_state(
        date_fd: int,
        stage_fd: int,
        body: dict[str, Any],
        key: str,  # Any: validated JSON.
    ) -> None:
        name = body["names"][key]
        source = _exists(date_fd, name)
        staged = _exists(stage_fd, key)
        if source and staged:
            raise GroupJournalConflict(f"ambiguous duplicate {key}")
        if source and key in body["staged"]:
            raise GroupJournalConflict(f"staged {key} reappeared at source")
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
        body: dict[str, Any],  # Any: validated JSON.
        key: str,
        relative: str,
        chain: list[list[int]],
        hook: Barrier | None,
        progress: GroupRecoveryResult,
    ) -> None:
        progress.phase = f"{key}_identity"
        self._verify_member_state(date_fd, stage_fd, body, key)
        if _exists(date_fd, body["names"][key]):
            progress.phase = f"{key}_stage"
            self._stage_member(date_fd, stage_fd, body, key, relative, chain, hook)
        if not _exists(stage_fd, key):
            return
        # A previous call may have renamed this member but failed to fsync.
        # Do not attest that visible move as durable without acknowledging it.
        progress.phase = f"{key}_stage_confirmation"
        os.fsync(date_fd)
        os.fsync(stage_fd)
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
        body: dict[str, Any],  # Any: validated JSON.
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
        self._assert_stage_named(stage_fd, body)
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
        body: dict[str, Any],  # Any: validated JSON.
        key: str,
        relative: str,
        chain: list[list[int]],
        hook: Barrier | None,
        progress: GroupRecoveryResult,
    ) -> None:
        if _fingerprint(stage_fd, key) != body["members"][key]:
            raise GroupJournalConflict(f"replaced staged {key}")
        self._assert_stage_named(stage_fd, body)
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
        self._assert_stage_named(stage_fd, body)
        os.unlink(key, dir_fd=stage_fd)
        progress.possibly_unlinked += 1
        progress.possibly_unlinked_bytes += body["members"][key]["size"]
        os.fsync(stage_fd)
        progress.possibly_unlinked -= 1
        progress.possibly_unlinked_bytes -= body["members"][key]["size"]
        progress.removed += 1
        progress.removed_bytes += body["members"][key]["size"]
        if hook:
            hook(f"after_{key}_unlink")
