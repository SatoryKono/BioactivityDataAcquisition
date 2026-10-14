"""cleanup group recovery for cooperative, fail-closed POSIX cleanup."""

from __future__ import annotations

import errno
import os
from secrets import token_hex
from typing import Any

from .cleanup_group_members import GroupMemberRecovery
from .cleanup_group_schema import (
    _ORDER,
    _STAGE_PREFIX,
    _STAGE_TAG,
    Barrier,
    GroupJournalConflict,
    GroupRecoveryResult,
    _exists,
    _identity,
)


class GroupRecoveryCoordinator(GroupMemberRecovery):
    """cleanup group recovery responsibilities."""

    def _recover_body(
        self,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],  # Any: validated JSON.
        hook: Barrier | None,
        progress: GroupRecoveryResult,
    ) -> None:
        relative = body["relative_date"]
        with self._date(relative) as (date_fd, chain):
            if chain != body["chain"]:
                raise GroupJournalConflict("date or ancestor replaced")
            stage_name = f"{_STAGE_PREFIX}{operation_id}"
            stage_fd = self._operation_stage(
                journal_fd, operation_id, body, hook, progress
            )
            stage_identity = (
                [body["stage"]["dev"], body["stage"]["ino"]]
                if body["stage"] is not None
                else None
            )
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
                self._finish_operation(
                    journal_fd,
                    operation_id,
                    stage_name,
                    stage_identity,
                    stage_fd,
                    body,
                    hook,
                    progress,
                )
            finally:
                if stage_fd is not None:
                    os.close(stage_fd)

    def _operation_stage(
        self,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],  # Any: validated JSON.
        hook: Barrier | None,
        progress: GroupRecoveryResult,
    ) -> int | None:
        """Attest a freshly allocated inode before moving any payload member.

        A directory nonce survives restart and detects inode reuse. Unsupported
        directory xattrs fail closed; a crash before association leaves an orphan
        which is never adopted solely from its reserved name.
        """
        name = f"{_STAGE_PREFIX}{operation_id}"
        progress.phase = "stage_association"
        if body["stage"] is None:
            return self._create_operation_stage(journal_fd, operation_id, body, hook)
        fd = self._private_dir(name, create=False)
        if fd is None:
            if body["state"] != "completed":
                raise GroupJournalConflict("associated stage disappeared")
            self._replace_record(journal_fd, operation_id, body)
            return None
        try:
            self._check_stage(fd, body["stage"])
            # A prior fsync error may have left a visible but uncertain record.
            # Re-establish its durable association before any move or retirement.
            self._replace_record(journal_fd, operation_id, body)
            return fd
        except BaseException:
            os.close(fd)
            raise

    def _create_operation_stage(
        self,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],  # Any: validated JSON.
        hook: Barrier | None,
    ) -> int:
        """Create and bind a stage, retiring only our unassociated empty inode."""
        name = f"{_STAGE_PREFIX}{operation_id}"
        fd = self._private_dir(name, create=True, exclusive=True)
        assert fd is not None
        association_started = False
        try:
            if hook:
                hook("after_stage_create")
            setter = os.__dict__.get("setxattr")
            if setter is None:
                raise OSError(errno.ENOTSUP, "directory xattrs unavailable")
            token = token_hex(16)
            setter(fd, _STAGE_TAG, token.encode(), flags=getattr(os, "XATTR_CREATE", 1))
            os.fsync(fd)
            os.fsync(self._root_fd)
            dev, ino = _identity(fd)
            association_started = True
            body["stage"] = {"dev": dev, "ino": ino, "token": token}
            self._replace_record(journal_fd, operation_id, body)
            if hook:
                hook("after_stage_association_fsync")
            return fd
        except BaseException:
            try:
                if not association_started:
                    self._discard_created_empty_dir(name, fd)
            finally:
                os.close(fd)
            raise

    def _apply_group(
        self,
        date_fd: int,
        stage_fd: int,
        journal_fd: int,
        operation_id: str,
        body: dict[str, Any],  # Any: validated JSON.
        relative: str,
        chain: list[list[int]],
        hook: Barrier | None,
        progress: GroupRecoveryResult,
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
        body: dict[str, Any],  # Any: validated JSON.
        relative: str,
        chain: list[list[int]],
        hook: Barrier | None,
        progress: GroupRecoveryResult,
    ) -> None:
        progress.phase = "completion"
        if hook:
            hook("before_completion")
        if stage_fd is not None:
            self._assert_stage_named(stage_fd, body)

        def absent() -> bool:
            return (
                chain == self._current_chain(relative)
                and not (
                    "copy" not in body["members"]
                    and _exists(date_fd, body["names"]["copy"])
                )
                and not any(
                    _exists(date_fd, body["names"][key])
                    or (stage_fd is not None and _exists(stage_fd, key))
                    for key in body["members"]
                )
            )

        if not absent():
            raise GroupJournalConflict("group is not durably absent")
        # Visible absence after an earlier failed fsync is not durable evidence.
        os.fsync(date_fd)
        if stage_fd is not None:
            os.fsync(stage_fd)
            self._assert_stage_named(stage_fd, body)
        if not absent():
            raise GroupJournalConflict("group changed during absence confirmation")
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
        stage_fd: int | None,
        body: dict[str, Any],  # Any: validated JSON.
        hook: Barrier | None,
        progress: GroupRecoveryResult,
    ) -> None:
        progress.phase = "finalize"
        if _exists(self._root_fd, stage_name):
            named = os.stat(stage_name, dir_fd=self._root_fd, follow_symlinks=False)
            if (
                stage_identity is None
                or stage_fd is None
                or [named.st_dev, named.st_ino] != stage_identity
            ):
                raise GroupJournalConflict("group stage directory replaced")
            self._check_stage(stage_fd, body["stage"])
            os.rmdir(stage_name, dir_fd=self._root_fd)
        # A retry must acknowledge an earlier rmdir whose fsync failed too.
        os.fsync(self._root_fd)
        if hook:
            hook("before_journal_unlink")
        self._assert_record(journal_fd, operation_id)
        os.unlink(f"{operation_id}.json", dir_fd=journal_fd)
        os.fsync(journal_fd)
        self._record_witnesses.pop(operation_id, None)
        if hook:
            hook("after_journal_unlink")
