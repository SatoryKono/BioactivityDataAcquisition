"""Bounded read-only Bronze cleanup preview traversal."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from pathlib import Path

from bioetl.domain.types import JsonDict

from .cleanup_core import valid_bronze_scope_name
from .cleanup_support import (
    candidate_is_safe,
    date_dir_name_is_older,
    real_root,
    root_components_safe,
    safe_named_child_dir,
    stat_is_link_or_reparse,
    validate_scope_filter,
)

_PREVIEW_MAX_ENTRIES = 100_000


def _consume_preview_entry(budget: list[int]) -> None:
    budget[0] += 1
    if budget[0] > _PREVIEW_MAX_ENTRIES:
        raise ValueError("Bronze preview exceeds 100000 filesystem entries")


class BronzeCleanupPreviewMixin:
    """Read-only, bounded preview over supported Bronze layouts."""

    base_path: Path
    _flat_structure: bool

    def preview_cleanup(
        self,
        provider: str | None = None,
        entity: str | None = None,
    ) -> JsonDict:  # Any: preview payload has heterogeneous values
        """Preview direct date-partition files with bounded, no-follow traversal."""
        validate_scope_filter(provider, "provider")
        validate_scope_filter(entity, "entity")
        from .cleanup_support import validate_flat_scope_compatibility
        validate_flat_scope_compatibility(self._flat_structure, provider, entity)
        preview_root = self._resolve_bronze_preview_root(provider, entity)
        exists = self.base_path.exists()
        if not exists or (self._flat_structure and (provider or entity)):
            return {
                "path": str(preview_root),
                "file_count": 0,
                "exists": exists and not (provider or entity),
            }
        if not root_components_safe(self.base_path):
            return {"path": str(preview_root), "file_count": 0, "exists": False}
        root_abs = Path(os.path.abspath(self.base_path))  # noqa: PTH100
        root_real = real_root(self.base_path)
        budget = [0]
        date_parents, scope_exists = self._preview_date_parents(
            provider, entity, root_real, budget
        )
        file_count = self._count_preview_files(
            date_parents, root_abs, root_real, budget
        )
        return {
            "path": str(preview_root),
            "file_count": file_count,
            "exists": scope_exists,
        }

    def _preview_date_parents(
        self,
        provider: str | None,
        entity: str | None,
        root_real: Path,
        budget: list[int],
    ) -> tuple[list[Path], bool]:
        """Resolve bounded preview scopes without following child links."""
        if self._flat_structure:
            return [self.base_path], True
        providers = self._preview_providers(provider, root_real, budget)
        date_parents: list[Path] = []
        for provider_dir in providers:
            if entity:
                child = safe_named_child_dir(provider_dir, entity, root_real)
                if child is not None:
                    _consume_preview_entry(budget)
                    date_parents.append(child)
            else:
                date_parents.extend(
                    self._iter_bounded_dirs(provider_dir, budget, scope=True)
                )
        if entity:
            return date_parents, bool(date_parents)
        if provider:
            return date_parents, bool(providers)
        return date_parents, True

    def _preview_providers(
        self, provider: str | None, root_real: Path, budget: list[int]
    ) -> list[Path]:
        """Select a named provider or stream bounded canonical scopes."""
        if provider:
            named = safe_named_child_dir(self.base_path, provider, root_real)
            if named is None:
                return []
            _consume_preview_entry(budget)
            return [named]
        return list(self._iter_bounded_dirs(self.base_path, budget, scope=True))

    def _count_preview_files(
        self,
        date_parents: list[Path],
        root_abs: Path,
        root_real: Path,
        budget: list[int],
    ) -> int:
        """Count only direct, safe date-partition files up to the public bound."""
        file_count = 0
        for parent in date_parents:
            for date_dir in self._iter_bounded_dirs(parent, budget):
                if not (
                    date_dir_name_is_older(date_dir.name, "9999-12-31")
                    or date_dir.name == "9999-12-31"
                ):
                    continue
                file_count += self._count_preview_date_files(
                    date_dir, root_abs, root_real, budget
                )
        return file_count

    @staticmethod
    def _iter_bounded_dirs(
        parent: Path, budget: list[int], *, scope: bool = False
    ) -> Iterator[Path]:
        try:
            with os.scandir(parent) as entries:
                for entry in entries:
                    _consume_preview_entry(budget)
                    try:
                        identity = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if (
                        stat.S_ISDIR(identity.st_mode)
                        and not stat_is_link_or_reparse(identity)
                        and (not scope or valid_bronze_scope_name(entry.name))
                    ):
                        yield Path(entry.path)
        except OSError:
            return

    @staticmethod
    def _count_preview_date_files(
        date_dir: Path, root_abs: Path, root_real: Path, budget: list[int]
    ) -> int:
        try:
            date_stat = date_dir.lstat()
        except OSError:
            return 0
        if not candidate_is_safe(
            date_dir, root_abs, root_real, date_stat, directory=True
        ):
            return 0
        count = 0
        try:
            with os.scandir(date_dir) as entries:
                for entry in entries:
                    _consume_preview_entry(budget)
                    try:
                        entry.stat(follow_symlinks=False)
                        identity = (date_dir / entry.name).lstat()
                    except OSError:
                        continue
                    if stat.S_ISREG(identity.st_mode) and candidate_is_safe(
                        date_dir / entry.name, root_abs, root_real, identity
                    ):
                        count += 1
        except OSError:
            return 0
        return count

    def _resolve_bronze_preview_root(
        self,
        provider: str | None,
        entity: str | None,
    ) -> Path:
        """Resolve Bronze preview root for optional provider/entity filters."""
        if self._flat_structure:
            return self.base_path
        if provider and entity:
            return self.base_path / provider / entity
        if provider:
            return self.base_path / provider
        return self.base_path
