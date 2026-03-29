"""File-backed lineage fragment persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.ports import LineageStorePort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)

__all__ = ["FileLineageStore"]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


def _stable_key_filename(key: str) -> str:
    """Return a filesystem-safe filename stem for one semantic key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _load_fragment_ids(index_path: Path, *, key: str) -> list[str]:
    """Load fragment identifiers from one JSONL index file."""
    if not index_path.exists():
        return []
    fragment_ids: dict[str, None] = {}
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            continue
        if str(payload.get("key")) != key:
            continue
        fragment_id = payload.get("fragment_id")
        if fragment_id is None:
            continue
        fragment_ids[str(fragment_id)] = None
    return list(fragment_ids)


@dataclass(slots=True)
class FileLineageStore(LineageStorePort):
    """Persist lineage graph fragments under the control-plane output tree."""

    base_path: Path
    metrics: MetricsPort | None = None

    def save(self, fragment: LineageGraphFragment) -> None:
        """Persist one fragment JSON and maintain lightweight lookup indexes."""
        fragments_dir = self.base_path / "fragments"
        fragments_dir.mkdir(parents=True, exist_ok=True)
        fragment_path = self._fragment_path(fragment.fragment_id)
        fragment_path.write_text(
            json.dumps(fragment.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

        if fragment.run_id is not None:
            self._append_index(
                self._run_index_path(fragment.run_id),
                key=fragment.run_id,
                fragment_id=fragment.fragment_id,
            )
        if fragment.manifest_id is not None:
            self._append_index(
                self._manifest_index_path(fragment.manifest_id),
                key=fragment.manifest_id,
                fragment_id=fragment.fragment_id,
            )
        for node in fragment.nodes:
            self._append_index(
                self._node_index_path(node.node_id),
                key=node.node_id,
                fragment_id=fragment.fragment_id,
            )

    def get(self, fragment_id: str) -> LineageGraphFragment | None:
        """Load one fragment by identifier if present."""
        started_at = perf_counter()
        status = "success"
        try:
            fragment = self._load_fragment(fragment_id)
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

    def _append_index(self, index_path: Path, *, key: str, fragment_id: str) -> None:
        """Append one fragment identifier to a JSONL lookup index."""
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {"key": key, "fragment_id": fragment_id},
                    sort_keys=True,
                )
            )
            handle.write("\n")

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
        return fragment if fragment.fragment_id == fragment_id else None
