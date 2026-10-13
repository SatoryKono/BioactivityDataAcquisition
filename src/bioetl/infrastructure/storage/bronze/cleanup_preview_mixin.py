"""Bounded read-only Bronze cleanup preview traversal."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from bioetl.domain.types import JsonDict

from .cleanup_support import (
    candidate_is_safe,
    date_dir_name_is_older,
    iter_safe_child_dirs,
    iter_writer_scope_dirs,
    real_root,
    root_components_safe,
    safe_named_child_dir,
    scan_dir_entries,
    validate_scope_filter,
)


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
        date_parents, scope_exists = self._preview_date_parents(
            provider, entity, root_real
        )
        file_count = self._count_preview_files(date_parents, root_abs, root_real)
        return {
            "path": str(preview_root),
            "file_count": file_count,
            "exists": scope_exists,
        }

    def _preview_date_parents(
        self, provider: str | None, entity: str | None, root_real: Path
    ) -> tuple[list[Path], bool]:
        """Resolve bounded preview scopes without following child links."""
        if self._flat_structure:
            return [self.base_path], True
        if provider:
            named = safe_named_child_dir(self.base_path, provider, root_real)
            providers = [named] if named is not None else []
        else:
            providers = iter_writer_scope_dirs(self.base_path)
        date_parents: list[Path] = []
        for provider_dir in providers:
            if entity:
                child = safe_named_child_dir(provider_dir, entity, root_real)
                if child is not None:
                    date_parents.append(child)
            else:
                date_parents.extend(iter_writer_scope_dirs(provider_dir))
        if entity:
            return date_parents, bool(date_parents)
        if provider:
            return date_parents, bool(providers)
        return date_parents, True

    def _count_preview_files(
        self, date_parents: list[Path], root_abs: Path, root_real: Path
    ) -> int:
        """Count only direct, safe date-partition files up to the public bound."""
        file_count = 0
        for parent in date_parents:
            for date_dir in iter_safe_child_dirs(parent):
                if not (
                    date_dir_name_is_older(date_dir.name, "9999-12-31")
                    or date_dir.name == "9999-12-31"
                ):
                    continue
                file_count += self._count_preview_date_files(
                    date_dir, root_abs, root_real
                )
                if file_count > 100_000:
                    raise ValueError("Bronze preview exceeds 100000 files")
        return file_count

    @staticmethod
    def _count_preview_date_files(
        date_dir: Path, root_abs: Path, root_real: Path
    ) -> int:
        try:
            date_stat = date_dir.lstat()
        except OSError:
            return 0
        if not candidate_is_safe(
            date_dir, root_abs, root_real, date_stat, directory=True
        ):
            return 0
        entries = scan_dir_entries(date_dir)
        if entries is None:
            return 0
        count = 0
        for entry in entries:
            try:
                entry.stat(follow_symlinks=False)
                identity = (date_dir / entry.name).lstat()
            except OSError:
                continue
            if stat.S_ISREG(identity.st_mode) and candidate_is_safe(
                date_dir / entry.name, root_abs, root_real, identity
            ):
                count += 1
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
