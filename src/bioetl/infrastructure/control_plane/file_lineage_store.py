"""File-backed lineage fragment persistence."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.ports import LineageStorePort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._durability import (
    flush_control_plane_file_descriptor,
)
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileLineageStore"]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


_LINEAGE_APPEND_OPEN_FLAGS = os.O_APPEND | os.O_CREAT | os.O_WRONLY


class _LineageIndexCorruptionError(ValueError):
    """Raised when a lineage index JSONL file is truncated or malformed."""


def _stable_key_filename(key: str) -> str:
    """Return a filesystem-safe filename stem for one semantic key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _build_stored_fragment_id(fragment: LineageGraphFragment) -> str:
    """Return one occurrence-scoped stored fragment identity."""
    anchors = [fragment.fragment_id]
    if fragment.run_id is not None:
        anchors.append(fragment.run_id)
    if fragment.manifest_id is not None:
        anchors.append(fragment.manifest_id)
    if len(anchors) == 1:
        return fragment.fragment_id
    digest = hashlib.sha256("|".join(anchors).encode("utf-8")).hexdigest()[:12]
    return f"{fragment.fragment_id}:occurrence:{digest}"


def _load_fragment_ids(index_path: Path, *, key: str) -> list[str]:
    """Load fragment identifiers from one JSONL index file."""
    if not index_path.exists():
        return []
    raw_text = index_path.read_text(encoding="utf-8")
    if not raw_text.strip():
        return []
    if not raw_text.endswith(("\n", "\r")):
        raise _LineageIndexCorruptionError(
            f"Lineage index '{index_path}' is corrupted: truncated tail line"
        )
    fragment_ids: dict[str, None] = {}
    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise _LineageIndexCorruptionError(
                f"Lineage index '{index_path}' is corrupted at line "
                f"{line_number}: {error.msg}"
            ) from error
        if not isinstance(payload, dict):
            raise _LineageIndexCorruptionError(
                f"Lineage index '{index_path}' is corrupted at line "
                f"{line_number}: payload must be a JSON object"
            )
        if str(payload.get("key")) != key:
            raise _LineageIndexCorruptionError(
                f"Lineage index '{index_path}' is corrupted at line "
                f"{line_number}: unexpected key"
            )
        fragment_id = payload.get("fragment_id")
        if fragment_id is None or not str(fragment_id).strip():
            raise _LineageIndexCorruptionError(
                f"Lineage index '{index_path}' is corrupted at line "
                f"{line_number}: missing fragment_id"
            )
        fragment_ids[str(fragment_id)] = None
    return list(fragment_ids)


def _truncate_index_to_offset(path: Path, *, offset: int) -> None:
    """Best-effort rollback of one lineage index file to a known-good offset."""
    if not path.exists():
        return
    file_descriptor = os.open(path, os.O_RDWR)
    try:
        os.ftruncate(file_descriptor, offset)
        flush_control_plane_file_descriptor(file_descriptor)
    finally:
        os.close(file_descriptor)


def _append_jsonl_payload(path: Path, payload: bytes) -> int:
    """Append one full JSONL payload with rollback on partial writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor = os.open(path, _LINEAGE_APPEND_OPEN_FLAGS, 0o666)
    bytes_written = 0
    checkpoint_size = 0
    try:
        checkpoint_size = os.fstat(file_descriptor).st_size
        while bytes_written < len(payload):
            written = os.write(file_descriptor, payload[bytes_written:])
            if written <= 0:
                raise OSError("Lineage index append produced an empty write")
            bytes_written += written
        flush_control_plane_file_descriptor(file_descriptor)
        return checkpoint_size
    except OSError:
        if bytes_written > 0:
            try:
                os.ftruncate(file_descriptor, checkpoint_size)
                flush_control_plane_file_descriptor(file_descriptor)
            except OSError:
                pass
        raise
    finally:
        os.close(file_descriptor)


@dataclass(slots=True)
class FileLineageStore(LineageStorePort):
    """Persist lineage graph fragments under the control-plane output tree."""

    base_path: Path
    metrics: MetricsPort | None = None

    def save(self, fragment: LineageGraphFragment) -> None:
        """Persist one fragment JSON and maintain lightweight lookup indexes."""
        fragments_dir = self.base_path / "fragments"
        fragments_dir.mkdir(parents=True, exist_ok=True)
        stored_fragment_id = fragment.stored_fragment_id or _build_stored_fragment_id(
            fragment
        )
        persisted_fragment = replace(
            fragment,
            stored_fragment_id=stored_fragment_id,
        )
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
            index_rollbacks.append(
                self._append_index(
                    self._semantic_fragment_index_path(fragment.fragment_id),
                    key=fragment.fragment_id,
                    fragment_id=stored_fragment_id,
                )
            )

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
        except (OSError, TypeError, ValueError):
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
            raise

    def get_occurrence(self, fragment_id: str) -> LineageGraphFragment | None:
        """Load one stored occurrence fragment id without semantic fallback."""
        started_at = perf_counter()
        status = "success"
        try:
            fragment = self._load_fragment(fragment_id)
            if fragment is None:
                status = "miss"
            return fragment
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="lineage",
                operation="get_occurrence",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def get(self, fragment_id: str) -> LineageGraphFragment | None:
        """Load one fragment by identifier if present."""
        started_at = perf_counter()
        status = "success"
        try:
            fragment = self._load_fragment(fragment_id)
            if fragment is None:
                stored_fragment_ids = _load_fragment_ids(
                    self._semantic_fragment_index_path(fragment_id),
                    key=fragment_id,
                )
                if not stored_fragment_ids:
                    status = "miss"
                    return None
                if len(stored_fragment_ids) > 1:
                    status = "failed"
                    raise ValueError(
                        "Semantic lineage fragment id resolves to multiple stored "
                        "occurrence records; use run_id or manifest_id lookup for "
                        "historical reconstruction"
                    )
                fragment = self._load_fragment(stored_fragment_ids[0])
                if fragment is None:
                    status = "miss"
                    return None
            return fragment
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="lineage",
                operation="get",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def list_by_run_id(self, run_id: RunID) -> list[LineageGraphFragment]:
        """Return fragments linked to one run identifier."""
        started_at = perf_counter()
        status = "success"
        try:
            fragments = self._load_from_index(
                self._run_index_path(str(run_id)),
                key=str(run_id),
            )
            if not fragments:
                status = "miss"
            return fragments
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="lineage",
                operation="list_by_run_id",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def list_by_manifest_id(self, manifest_id: str) -> list[LineageGraphFragment]:
        """Return fragments linked to one manifest identifier."""
        started_at = perf_counter()
        status = "success"
        try:
            fragments = self._load_from_index(
                self._manifest_index_path(manifest_id),
                key=manifest_id,
            )
            if not fragments:
                status = "miss"
            return fragments
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="lineage",
                operation="list_by_manifest_id",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def list_by_node_id(self, node_id: str) -> list[LineageGraphFragment]:
        """Return fragments that mention one node identifier."""
        started_at = perf_counter()
        status = "success"
        try:
            fragments = self._load_from_index(
                self._node_index_path(node_id),
                key=node_id,
            )
            if not fragments:
                status = "miss"
            return fragments
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="lineage",
                operation="list_by_node_id",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def _fragment_path(self, fragment_id: str) -> Path:
        """Resolve the fragment JSON path for one fragment identifier."""
        return (
            self.base_path / "fragments" / f"{_stable_key_filename(fragment_id)}.json"
        )

    def _run_index_path(self, run_id: str) -> Path:
        """Resolve the run-id index path."""
        return self.base_path / "_by_run_id" / f"{_stable_key_filename(run_id)}.jsonl"

    def _semantic_fragment_index_path(self, fragment_id: str) -> Path:
        """Resolve the semantic-fragment index path."""
        return (
            self.base_path
            / "_by_fragment_id"
            / f"{_stable_key_filename(fragment_id)}.jsonl"
        )

    def _manifest_index_path(self, manifest_id: str) -> Path:
        """Resolve the manifest-id index path."""
        return (
            self.base_path
            / "_by_manifest_id"
            / f"{_stable_key_filename(manifest_id)}.jsonl"
        )

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

    def _load_from_index(
        self,
        index_path: Path,
        *,
        key: str,
    ) -> list[LineageGraphFragment]:
        """Load fragments referenced by one lookup index."""
        fragments: list[LineageGraphFragment] = []
        for fragment_id in _load_fragment_ids(index_path, key=key):
            fragment = self._load_fragment(fragment_id)
            if fragment is not None:
                fragments.append(fragment)
        return fragments

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
