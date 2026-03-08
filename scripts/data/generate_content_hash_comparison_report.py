"""Generate comparison report for legacy vs current content hash algorithm."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.constants import META_FIELDS
from bioetl.domain.serialization import serialize_to_json_canonical
from bioetl.domain.transformations import _normalize_value, generate_content_hash


def _legacy_generate_content_hash(record: dict[str, Any], provider: str) -> str:
    """Legacy behavior before include/exclude + _dq_* exclusion support."""
    normalized = {
        key: _normalize_value(value)
        for key, value in record.items()
        if key not in META_FIELDS
    }
    payload = f"{provider}{serialize_to_json_canonical(normalized)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_content_hash_config(
    provider: str, entity: str
) -> tuple[set[str] | None, set[str]]:
    unified_entity_path = Path("configs/entities") / provider / f"{entity}.yaml"
    if unified_entity_path.exists():
        unified_data = yaml.safe_load(unified_entity_path.read_text()) or {}
        schema_section = (
            unified_data.get("schema", {}) if isinstance(unified_data, dict) else {}
        )
        cfg = (
            schema_section.get("content_hash", {})
            if isinstance(schema_section, dict)
            else {}
        )
    else:
        # Legacy fallback kept for historical snapshots.
        schema_path = Path("configs/schemas") / provider / f"{entity}.yaml"
        if not schema_path.exists():
            return None, set()
        data = yaml.safe_load(schema_path.read_text()) or {}
        cfg = data.get("content_hash", {}) if isinstance(data, dict) else {}

    include = set(cfg.get("include", [])) if isinstance(cfg, dict) else set()
    exclude = set(cfg.get("exclude", [])) if isinstance(cfg, dict) else set()
    return (include or None), exclude


def main() -> None:
    snapshot_path = Path("tests/snapshots/content_hash_records.json")
    report_path = Path("tests/snapshots/content_hash_comparison.md")

    rows = json.loads(snapshot_path.read_text())
    changed = 0
    lines = [
        "# Content Hash Comparison Report",
        "",
        f"Snapshot source: `{snapshot_path}`",
        "",
        "| provider | entity | record_id | old_hash | new_hash | changed |",
        "|---|---|---|---|---|---|",
    ]

    for row in rows:
        provider = row["provider"]
        entity = row["entity"]
        record_id = row["record_id"]
        record = row["record"]

        include_fields, exclude_fields = _load_content_hash_config(provider, entity)
        old_hash = _legacy_generate_content_hash(record, provider)
        new_hash = str(
            generate_content_hash(
                record,
                provider,
                exclude_none=False,
                include_fields=include_fields,
                exclude_fields=exclude_fields,
            )
        )
        is_changed = old_hash != new_hash
        if is_changed:
            changed += 1

        lines.append(
            f"| {provider} | {entity} | {record_id} | `{old_hash[:12]}…` | `{new_hash[:12]}…` | {'yes' if is_changed else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Summary",
            f"- Total records: {len(rows)}",
            f"- Changed hashes: {changed}",
            f"- Unchanged hashes: {len(rows) - changed}",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
