#!/usr/bin/env python3
"""Run a local mock server for quarantine explorer API smoke checks.

This script starts BioETL HealthServer with a read-only mock quarantine service
implementing:
  - GET /ops/quarantine/filtered-records
  - GET /ops/quarantine/filtered-record/{payload_hash}
  - GET /ops/quarantine/filtered-stats
  - GET /ops/quarantine/filter-options
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from bioetl.interfaces.http.health_server import HealthServer
except ModuleNotFoundError:
    root = Path(__file__).resolve().parents[3]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from bioetl.interfaces.http.health_server import HealthServer

JsonDict = dict[str, Any]


def _payload_preview(payload: JsonDict) -> JsonDict:
    keys = list(payload.keys())
    preview: JsonDict = {key: payload[key] for key in keys[:8]}
    if len(keys) > 8:
        preview["_truncated_keys"] = len(keys) - 8
    return preview


_SAMPLE_ROWS: list[JsonDict] = [
    {
        "ingestion_ts": "2026-04-06T08:15:00Z",
        "pipeline": "chembl_activity",
        "run_id": "chembl-run-001",
        "run_type": "incremental",
        "payload_hash": "sha256:chembl-001",
        "reason_code": "required_field_missing",
        "rule_type": "structural_policy",
        "field": "canonical_smiles",
        "operator": "required",
        "expected": "non-empty string",
        "actual": None,
        "dq_status": "NEW",
        "reason": "Required field missing",
        "payload": {
            "activity_id": 101,
            "molecule_chembl_id": "CHEMBL25",
            "canonical_smiles": None,
        },
    },
    {
        "ingestion_ts": "2026-04-06T08:20:00Z",
        "pipeline": "chembl_activity",
        "run_id": "chembl-run-001",
        "run_type": "incremental",
        "payload_hash": "sha256:chembl-002",
        "reason_code": "range_filter_mismatch",
        "rule_type": "bounded_range_policy",
        "field": "pchembl_value",
        "operator": "between",
        "expected": "[0.0, 15.0]",
        "actual": 22.1,
        "dq_status": "NEW",
        "reason": "pChEMBL out of accepted bounds",
        "payload": {
            "activity_id": 102,
            "molecule_chembl_id": "CHEMBL42",
            "pchembl_value": 22.1,
        },
    },
    {
        "ingestion_ts": "2026-04-06T08:45:00Z",
        "pipeline": "pubchem_activity",
        "run_id": "pubchem-run-010",
        "run_type": "full",
        "payload_hash": "sha256:pubchem-010",
        "reason_code": "enum_violation",
        "rule_type": "semantic_policy",
        "field": "activity_outcome",
        "operator": "in_set",
        "expected": "['active','inactive','inconclusive']",
        "actual": "ambiguous",
        "dq_status": "NEW",
        "reason": "Unsupported activity outcome value",
        "payload": {
            "aid": 22001,
            "sid": 44007,
            "activity_outcome": "ambiguous",
        },
    },
]

for _row in _SAMPLE_ROWS:
    payload_obj = _row.get("payload")
    if isinstance(payload_obj, dict):
        _row["payload_preview"] = _payload_preview(payload_obj)
    else:
        _row["payload_preview"] = {"value": payload_obj}


def _normalize_multi(raw: str | None) -> set[str] | None:
    if raw is None:
        return None
    values = {item.strip() for item in raw.split(",") if item.strip()}
    if not values:
        return None
    lowered = {item.lower() for item in values}
    if lowered <= {"*", "all", "__all", ".*"}:
        return None
    return {item for item in values if item.lower() not in {"*", "all", "__all", ".*"}}


def _matches(value: object, allowed: set[str] | None) -> bool:
    if allowed is None:
        return True
    return isinstance(value, str) and value in allowed


def _parse_iso(ts: str | None) -> datetime | None:
    if ts is None:
        return None
    candidate = ts.strip()
    if not candidate:
        return None
    parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clip_payload(rows: list[JsonDict]) -> list[JsonDict]:
    clipped: list[JsonDict] = []
    for row in rows:
        item = dict(row)
        item.pop("payload", None)
        clipped.append(item)
    return clipped


def _scoped_allowed_values(
    *,
    pipeline: str | None,
    run_type: str | None,
    reason_code: str | None,
    field: str | None,
    run_id: str | None,
    payload_hash: str | None,
) -> tuple[
    set[str] | None,
    set[str] | None,
    set[str] | None,
    set[str] | None,
    set[str] | None,
    set[str] | None,
]:
    return (
        _normalize_multi(pipeline),
        _normalize_multi(run_type),
        _normalize_multi(reason_code),
        _normalize_multi(field),
        _normalize_multi(run_id),
        _normalize_multi(payload_hash),
    )


def _row_matches_scope(
    row: JsonDict,
    *,
    pipeline_allowed: set[str] | None,
    run_type_allowed: set[str] | None,
    reason_allowed: set[str] | None,
    field_allowed: set[str] | None,
    run_id_allowed: set[str] | None,
    payload_hash_allowed: set[str] | None,
    from_bound: datetime | None,
    to_bound: datetime | None,
) -> bool:
    if not _matches(row.get("pipeline"), pipeline_allowed):
        return False
    if not _matches(row.get("run_type"), run_type_allowed):
        return False
    if not _matches(row.get("reason_code"), reason_allowed):
        return False
    if not _matches(row.get("field"), field_allowed):
        return False
    if not _matches(row.get("run_id"), run_id_allowed):
        return False
    if not _matches(row.get("payload_hash"), payload_hash_allowed):
        return False

    row_ts = _parse_iso(str(row.get("ingestion_ts", "")))
    if from_bound is not None and (row_ts is None or row_ts < from_bound):
        return False
    if to_bound is not None and (row_ts is None or row_ts > to_bound):
        return False
    return True


class MockQuarantineExplorerService:
    """Minimal async service compatible with HealthServer quarantine endpoints."""

    def __init__(self) -> None:
        self._rows = [dict(row) for row in _SAMPLE_ROWS]
        self._bronze_records_by_pipeline = {
            "chembl_activity": 1200,
            "pubchem_activity": 900,
        }

    def _scoped_rows(
        self,
        *,
        pipeline: str | None,
        run_type: str | None,
        reason_code: str | None,
        field: str | None,
        run_id: str | None,
        payload_hash: str | None,
        from_ts: str | None,
        to_ts: str | None,
    ) -> list[JsonDict]:
        (
            pipeline_allowed,
            run_type_allowed,
            reason_allowed,
            field_allowed,
            run_id_allowed,
            payload_hash_allowed,
        ) = _scoped_allowed_values(
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            payload_hash=payload_hash,
        )
        from_bound = _parse_iso(from_ts)
        to_bound = _parse_iso(to_ts)

        rows: list[JsonDict] = []
        for row in self._rows:
            if not _row_matches_scope(
                row,
                pipeline_allowed=pipeline_allowed,
                run_type_allowed=run_type_allowed,
                reason_allowed=reason_allowed,
                field_allowed=field_allowed,
                run_id_allowed=run_id_allowed,
                payload_hash_allowed=payload_hash_allowed,
                from_bound=from_bound,
                to_bound=to_bound,
            ):
                continue
            rows.append(dict(row))
        return rows

    async def list_filtered_records(
        self,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        payload_hash: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "ingestion_ts_desc",
    ) -> JsonDict:
        await asyncio.sleep(0)
        rows = self._scoped_rows(
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            payload_hash=payload_hash,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        rows = _clip_payload(rows)
        reverse = sort != "ingestion_ts_asc"
        rows.sort(key=lambda row: str(row.get("ingestion_ts", "")), reverse=reverse)
        start = max(offset, 0)
        size = 50 if limit <= 0 else min(limit, 500)
        page = rows[start : start + size]
        return {
            "items": page,
            "total": len(rows),
            "limit": size,
            "offset": start,
        }

    async def get_filtered_record(
        self,
        *,
        payload_hash: str,
        pipeline: str | None = None,
    ) -> JsonDict | None:
        await asyncio.sleep(0)
        rows = self._scoped_rows(
            pipeline=pipeline,
            run_type=None,
            reason_code=None,
            field=None,
            run_id=None,
            payload_hash=payload_hash,
            from_ts=None,
            to_ts=None,
        )
        if not rows:
            return None
        rows.sort(key=lambda row: str(row.get("ingestion_ts", "")), reverse=True)
        row = dict(rows[0])
        row["cli_hint"] = (
            "bioetl quarantine resolve --pipeline "
            f"{row.get('pipeline', '')} --payload-hash {payload_hash} --status IGNORED"
        )
        return row

    async def get_filtered_stats(
        self,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        payload_hash: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> JsonDict:
        await asyncio.sleep(0)
        rows = self._scoped_rows(
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            payload_hash=payload_hash,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        by_reason = Counter(
            str(row.get("reason_code", "")).strip()
            for row in rows
            if str(row.get("reason_code", "")).strip()
        )
        by_field = Counter(
            str(row.get("field", "")).strip()
            for row in rows
            if str(row.get("field", "")).strip()
        )
        by_signature = Counter(
            " | ".join(
                [
                    str(row.get("reason_code", "")).strip(),
                    str(row.get("rule_type", "")).strip(),
                    str(row.get("field", "")).strip(),
                    str(row.get("operator", "")).strip(),
                ]
            )
            for row in rows
        )

        scoped_pipelines = {
            str(row.get("pipeline", "")).strip()
            for row in rows
            if str(row.get("pipeline", "")).strip()
        }
        bronze_records = sum(
            self._bronze_records_by_pipeline.get(pipeline_name, 0)
            for pipeline_name in scoped_pipelines
        )
        total = len(rows)
        reject_ratio = (total / bronze_records) if bronze_records else 0.0
        return {
            "total": total,
            "by_reason_code": [
                {"key": key, "count": count} for key, count in by_reason.most_common(20)
            ],
            "by_field": [
                {"key": key, "count": count} for key, count in by_field.most_common(20)
            ],
            "by_reason_signature": [
                {"key": key, "count": count}
                for key, count in by_signature.most_common(20)
                if key.strip(" |")
            ],
            "bronze_records": bronze_records,
            "reject_ratio": reject_ratio,
        }

    async def get_filtered_filter_options(
        self,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> JsonDict:
        await asyncio.sleep(0)
        rows = self._scoped_rows(
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            payload_hash=None,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        return {
            "pipelines": sorted(
                {
                    str(row.get("pipeline", "")).strip()
                    for row in rows
                    if row.get("pipeline")
                }
            ),
            "run_types": sorted(
                {
                    str(row.get("run_type", "")).strip()
                    for row in rows
                    if row.get("run_type")
                }
            ),
            "reason_codes": sorted(
                {
                    str(row.get("reason_code", "")).strip()
                    for row in rows
                    if row.get("reason_code")
                }
            ),
            "fields": sorted(
                {str(row.get("field", "")).strip() for row in rows if row.get("field")}
            ),
            "run_ids": sorted(
                {
                    str(row.get("run_id", "")).strip()
                    for row in rows
                    if row.get("run_id")
                }
            ),
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8081, help="Bind port")
    return parser


def _print_smoke_hints(host: str, port: int) -> None:
    # Local mock server smoke URL — plain HTTP is intentional (S5332).
    _scheme = "http"
    base_url = f"{_scheme}://{host}:{port}"
    print("\nMock Quarantine Explorer started.")
    print(f"Base URL: {base_url}")
    print("\nSmoke examples:")
    print(
        "curl -s "
        f"'{base_url}/ops/quarantine/filter-options?from=2026-04-06T00:00:00Z&to=2026-04-06T23:59:59Z' | jq"
    )
    print(
        "curl -s "
        f"'{base_url}/ops/quarantine/filtered-stats?pipeline=chembl_activity&run_type=incremental' | jq"
    )
    print(
        "curl -s "
        f"'{base_url}/ops/quarantine/filtered-records?pipeline=chembl_activity,pubchem_activity"
        "&run_type=incremental,full&reason_code=required_field_missing,range_filter_mismatch"
        "&field=canonical_smiles,pchembl_value&from=2026-04-06T00:00:00Z&to=2026-04-06T23:59:59Z"
        "&limit=50&offset=0&sort=ingestion_ts_desc' | jq"
    )
    print(
        "curl -s "
        f"'{base_url}/ops/quarantine/filtered-record/sha256:chembl-001?pipeline=chembl_activity' | jq"
    )
    print("\nStop with Ctrl+C.")


async def _run_server(host: str, port: int) -> None:
    service = MockQuarantineExplorerService()
    server = HealthServer(host=host, port=port, quarantine_service=service)
    await server.start()
    _print_smoke_hints(host, port)
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await server.stop()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(_run_server(host=args.host, port=args.port))
    except OSError as exc:
        print(
            "Failed to bind mock quarantine explorer server "
            f"on {args.host}:{args.port}: {exc}"
        )
        return 2
    except KeyboardInterrupt:
        print("\nShutting down mock quarantine explorer server.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
