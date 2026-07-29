"""File-backed lineage fragment persistence."""

from __future__ import annotations

import json
import os
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, override

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.ports import LineageStorePort
from bioetl.infrastructure.control_plane._durability import (
    flush_control_plane_file_descriptor,
)
from bioetl.infrastructure.control_plane._file_lineage_index import (
    LineageIndexCorruptionError,
    append_jsonl_payload,
    build_stored_fragment_id,
    load_fragment_ids,
    stable_key_filename,
    truncate_index_to_offset,
)
from bioetl.infrastructure.control_plane._file_lineage_queries import (
    FileLineageQueriesMixin,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileLineageStore"]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


_LINEAGE_APPEND_OPEN_FLAGS = os.O_APPEND | os.O_CREAT | os.O_WRONLY
_LineageIndexCorruptionError = LineageIndexCorruptionError


def _stable_key_filename(key: str) -> str:
    """Return a filesystem-safe filename stem for one semantic key."""
    return stable_key_filename(key)


def _build_stored_fragment_id(fragment: LineageGraphFragment) -> str:
    """Return one occurrence-scoped stored fragment identity."""
    return build_stored_fragment_id(fragment)


@override
def _load_fragment_ids(index_path: Path, *, key: str) -> list[str]:
    """Load fragment identifiers from one JSONL index file."""
    return load_fragment_ids(index_path, key=key)


def _truncate_index_to_offset(path: Path, *, offset: int) -> None:
    """Best-effort rollback of one lineage index file to a known-good offset."""
    truncate_index_to_offset(
        path,
        offset=offset,
        os_module=os,
        flush_file_descriptor=flush_control_plane_file_descriptor,
    )


def _append_jsonl_payload(path: Path, payload: bytes) -> int:
    """Append one full JSONL payload with public-module patch points."""
    return append_jsonl_payload(
        path,
        payload,
        open_flags=_LINEAGE_APPEND_OPEN_FLAGS,
        os_module=os,
        flush_file_descriptor=flush_control_plane_file_descriptor,
    )


@dataclass(slots=True)
class FileLineageStore(FileLineageQueriesMixin, LineageStorePort):
    """Persist lineage graph fragments under the control-plane output tree."""

    base_path: Path
    metrics: MetricsPort | None = None

    @override
    def save(self, fragment: LineageGraphFragment) -> None:
        """Persist one fragment JSON and maintain lightweight lookup indexes."""
        fragments_dir = self.base_path / "fragments"
        fragments_dir.mkdir(parents=True, exist_ok=True)
        stored_fragment_id = fragment.stored_fragment_id or _build_stored_fragment_id(
            fragment
        )
        persisted_fragment = replace(fragment, stored_fragment_id=stored_fragment_id)
        fragment_path = self._fragment_path(stored_fragment_id)
        existing_fragment_payload = (
            fragment_path.read_text(encoding="utf-8")
            if fragment_path.exists()
            else None
        )
        index_rollbacks: list[tuple[Path, int]] = []
        try:
            atomic_write_text(
                fragment_path,
                json.dumps(persisted_fragment.to_dict(), indent=2, sort_keys=True),
            )
            index_rollbacks.extend(self._fragment_indexes(fragment, stored_fragment_id))
        except (OSError, TypeError, ValueError):
            self._rollback_save(
                fragment_path=fragment_path,
                existing_fragment_payload=existing_fragment_payload,
                index_rollbacks=index_rollbacks,
            )
            raise

    def _fragment_indexes(
        self,
        fragment: LineageGraphFragment,
        stored_fragment_id: str,
    ) -> list[tuple[Path, int]]:
        """Append all lookup indexes for one persisted fragment."""
        index_rollbacks = [
            self._append_index(
                self._semantic_fragment_index_path(fragment.fragment_id),
                key=fragment.fragment_id,
                fragment_id=stored_fragment_id,
            )
        ]
        if fragment.run_id is not None:
            index_rollbacks.append(
                self._append_index(
                    self._run_index_path(fragment.run_id),
                    key=fragment.run_id,
                    fragment_id=stored_fragment_id,
                )
            )
        if fragment.manifest_id is not None:
            index_rollbacks.append(
                self._append_index(
                    self._manifest_index_path(fragment.manifest_id),
                    key=fragment.manifest_id,
                    fragment_id=stored_fragment_id,
                )
            )
        for node in fragment.nodes:
            index_rollbacks.append(
                self._append_index(
                    self._node_index_path(node.node_id),
                    key=node.node_id,
                    fragment_id=stored_fragment_id,
                )
            )
        return index_rollbacks

    def _rollback_save(
        self,
        *,
        fragment_path: Path,
        existing_fragment_payload: str | None,
        index_rollbacks: list[tuple[Path, int]],
    ) -> None:
        """Restore fragment and indexes after a failed save."""
        for index_path, checkpoint_offset in reversed(index_rollbacks):
            with suppress(OSError):
                _truncate_index_to_offset(index_path, offset=checkpoint_offset)
        if existing_fragment_payload is None:
            with suppress(OSError):
                if fragment_path.exists():
                    fragment_path.unlink()
        else:
            with suppress(OSError):
                atomic_write_text(fragment_path, existing_fragment_payload)

    def _fragment_path(self, fragment_id: str) -> Path:
        """Resolve the fragment JSON path for one fragment identifier."""
        return (
            self.base_path / "fragments" / f"{_stable_key_filename(fragment_id)}.json"
        )

    @override
    def _run_index_path(self, run_id: str) -> Path:
        """Resolve the run-id index path."""
        return self.base_path / "_by_run_id" / f"{_stable_key_filename(run_id)}.jsonl"

    @override
    def _semantic_fragment_index_path(self, fragment_id: str) -> Path:
        """Resolve the semantic-fragment index path."""
        return (
            self.base_path
            / "_by_fragment_id"
            / f"{_stable_key_filename(fragment_id)}.jsonl"
        )

    @override
    def _manifest_index_path(self, manifest_id: str) -> Path:
        """Resolve the manifest-id index path."""
        return (
            self.base_path
            / "_by_manifest_id"
            / f"{_stable_key_filename(manifest_id)}.jsonl"
        )

    @override
    def _node_index_path(self, node_id: str) -> Path:
        """Resolve the node-id index path."""
        return self.base_path / "_by_node_id" / f"{_stable_key_filename(node_id)}.jsonl"

    def _append_index(
        self, index_path: Path, *, key: str, fragment_id: str
    ) -> tuple[Path, int]:
        """Append one fragment identifier to a JSONL lookup index."""
        checkpoint_offset = _append_jsonl_payload(
            index_path,
            (
                json.dumps(
                    {"key": key, "fragment_id": fragment_id},
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8"),
        )
        return index_path, checkpoint_offset

    @override
    def _load_from_index(
        self,
        index_path: Path,
        *,
        key: str,
    ) -> list[LineageGraphFragment]:
        """Load fragments referenced by one lookup index."""
        fragments: list[LineageGraphFragment] = []
        for fragment_id in self._load_fragment_ids(index_path, key=key):
            fragment = self._load_fragment(fragment_id)
            if fragment is not None:
                fragments.append(fragment)
        return fragments

    @override
    def _load_fragment_ids(self, index_path: Path, *, key: str) -> list[str]:
        return _load_fragment_ids(index_path, key=key)

    @override
    def _load_fragment(self, fragment_id: str) -> LineageGraphFragment | None:
        """Load one fragment payload without emitting public lookup metrics."""
        fragment_path = self._fragment_path(fragment_id)
        if not fragment_path.exists():
            return None
        payload = json.loads(fragment_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Lineage fragment payload must be a JSON object")
        fragment = LineageGraphFragment.from_dict(payload)
        stored_fragment_id = fragment.stored_fragment_id
        if stored_fragment_id is not None:
            return fragment if stored_fragment_id == fragment_id else None
        return fragment if fragment.fragment_id == fragment_id else None
