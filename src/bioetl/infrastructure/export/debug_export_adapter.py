# pyright: reportReturnType=false
# basedpyright residual burn-down (shrink-only product surface).
"""Infrastructure adapter for persisted debug export audit packs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from bioetl.domain.types import DebugExportResult, RunID
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.export.debug_export_ops import (
    collect_headers,
    compute_pack_hash,
    fingerprint_artifact,
    normalize_csv_value,
    resolve_debug_export_root,
    write_debug_csv,
    write_debug_schema,
    write_debug_xlsx,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

if TYPE_CHECKING:
    from bioetl.domain.types import DebugExportPack

__all__ = ["DebugExportAdapter"]


class DebugExportAdapter:
    """Persist deterministic CSV/XLSX audit packs for debug export runs."""

    def __init__(
        self,
        *,
        lineage_store_path: str | None = None,
    ) -> None:
        self._lineage_store_path = lineage_store_path

    def write_pack(
        self,
        *,
        pack: DebugExportPack,
    ) -> DebugExportResult:
        root_path = self._resolve_root(pack)
        root_path.mkdir(parents=True, exist_ok=True)
        lineage_rows = tuple(self._load_lineage_rows(pack))
        tables = dict(pack.tables)
        if lineage_rows:
            tables["lineage"] = lineage_rows

        file_paths: list[str] = []
        canonical_artifacts: list[dict[str, object]] = []
        for table_name, rows in tables.items():
            csv_path = root_path / f"{table_name}.csv"
            schema_path = root_path / f"{table_name}.schema.json"
            self._write_csv(csv_path, rows, include_bom=pack.include_bom)
            self._write_schema(schema_path, rows)
            file_paths.extend((str(csv_path), str(schema_path)))
            canonical_artifacts.append(self._fingerprint(csv_path, root_path=root_path))
            canonical_artifacts.append(
                self._fingerprint(schema_path, root_path=root_path)
            )

        workbook_path: Path | None = None
        xlsx_skip_reason: str | None = None
        if "xlsx" in pack.formats:
            candidate_path = root_path / "debug_export.xlsx"
            try:
                self._write_xlsx(
                    candidate_path,
                    tables,
                    max_rows_per_sheet=pack.max_rows_per_sheet,
                )
            except ModuleNotFoundError as exc:
                if exc.name != "openpyxl":
                    raise
                xlsx_skip_reason = (
                    "openpyxl is not installed; CSV artifacts remain the source of truth"
                )
            else:
                workbook_path = candidate_path
                file_paths.append(str(workbook_path))

        debug_export_hash = self._compute_pack_hash(canonical_artifacts)
        manifest_path = root_path / "manifest.json"
        manifest_payload = {
            "run_id": pack.run_id,
            "workflow_id": pack.workflow_id,
            "pipeline_id": pack.pipeline_id,
            "provider_id": pack.provider_id,
            "manifest_id": pack.manifest_id,
            "status": pack.status,
            "created_at": pack.created_at.isoformat(),
            "debug_export_hash": debug_export_hash,
            "xlsx_skip_reason": xlsx_skip_reason,
            "files": canonical_artifacts
            + (
                [
                    self._fingerprint(
                        workbook_path,
                        include_content_hash=False,
                        root_path=root_path,
                    )
                ]
                if workbook_path is not None
                else []
            ),
        }
        atomic_write_text(
            manifest_path,
            json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n",
        )
        return DebugExportResult(
            root_path=str(root_path),
            manifest_path=str(manifest_path),
            debug_export_hash=debug_export_hash,
            file_paths=tuple(file_paths),
        )

    def _resolve_root(self, pack: DebugExportPack) -> Path:
        return resolve_debug_export_root(pack)

    def _write_csv(
        self,
        output_path: Path,
        rows: tuple[dict[str, object], ...],
        *,
        include_bom: bool,
    ) -> None:
        write_debug_csv(output_path, rows, include_bom=include_bom)

    def _write_schema(
        self,
        output_path: Path,
        rows: tuple[dict[str, object], ...],
    ) -> None:
        write_debug_schema(output_path, rows)

    def _write_xlsx(
        self,
        output_path: Path,
        tables: dict[str, tuple[dict[str, object], ...]],
        *,
        max_rows_per_sheet: int,
    ) -> None:
        write_debug_xlsx(
            output_path,
            tables,
            max_rows_per_sheet=max_rows_per_sheet,
        )

    def _collect_headers(
        self,
        rows: tuple[dict[str, object], ...],
    ) -> list[str]:
        return collect_headers(rows)

    def _normalize_csv_value(self, value: object | None) -> object:
        return normalize_csv_value(value)

    def _fingerprint(
        self,
        path: Path,
        *,
        include_content_hash: bool = True,
        root_path: Path | None = None,
    ) -> dict[str, object]:
        return fingerprint_artifact(
            path,
            include_content_hash=include_content_hash,
            root_path=root_path,
        )

    def _compute_pack_hash(
        self,
        artifacts: list[dict[str, object]],
    ) -> str:
        return compute_pack_hash(artifacts)

    def _load_lineage_fragments(self, pack: DebugExportPack) -> list[object]:
        # Keep FileLineageStore resolution in this module so unit tests can
        # monkeypatch bioetl.infrastructure.export.debug_export_adapter.FileLineageStore.
        if self._lineage_store_path is None:
            return []
        try:
            store = FileLineageStore(base_path=Path(self._lineage_store_path))
            if pack.manifest_id is not None:
                return list(store.list_by_manifest_id(pack.manifest_id))
            return list(store.list_by_run_id(RunID(UUID(pack.run_id))))
        except (OSError, TypeError, ValueError):
            return []

    @staticmethod
    def _lineage_rows_for_fragment(fragment: object) -> list[dict[str, object]]:
        # Lineage fragment is duck-typed from control-plane store (avoid hard import cycles).
        frag = cast(Any, fragment)
        rows: list[dict[str, object]] = []
        for node in frag.nodes:
            rows.append(
                {
                    "fragment_id": frag.fragment_id,
                    "stored_fragment_id": frag.stored_fragment_id,
                    "manifest_id": frag.manifest_id,
                    "run_id": frag.run_id,
                    "node_id": node.node_id,
                    "edge_type": "",
                    "related_node_id": "",
                    "node_type": node.node_type,
                }
            )
        for edge in frag.edges:
            rows.append(
                {
                    "fragment_id": frag.fragment_id,
                    "stored_fragment_id": frag.stored_fragment_id,
                    "manifest_id": frag.manifest_id,
                    "run_id": frag.run_id,
                    "node_id": edge.source.node_id,
                    "edge_type": edge.edge_type,
                    "related_node_id": edge.target.node_id,
                    "node_type": "",
                }
            )
        return rows

    def _load_lineage_rows(self, pack: DebugExportPack) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for fragment in self._load_lineage_fragments(pack):
            rows.extend(self._lineage_rows_for_fragment(fragment))
        return rows
