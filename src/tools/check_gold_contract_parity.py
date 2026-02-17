"""Check parity between Gold Pandera schemas and exported JSON contracts."""

from __future__ import annotations

import json
from pathlib import Path

from export_gold_contracts import (
    CONTRACTS_DIR,
    FieldSpec,
    _to_entity_name,
    extract_field_specs,
    get_gold_schema_classes,
)


def _read_exported_fields(path: Path) -> dict[str, FieldSpec]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        item["name"]: FieldSpec(
            name=item["name"],
            json_type=item["json_type"],
            nullable=item["nullable"],
            description=item.get("description"),
        )
        for item in payload.get("fields", [])
    }


def main() -> int:
    mismatches: list[str] = []

    for schema_cls in get_gold_schema_classes():
        entity_name = _to_entity_name(schema_cls.__name__)
        contract_path = CONTRACTS_DIR / f"{entity_name}_v1.0.json"
        if not contract_path.exists():
            mismatches.append(
                f"[{entity_name}] missing exported contract: {contract_path}"
            )
            continue

        pandera_fields = {item.name: item for item in extract_field_specs(schema_cls)}
        exported_fields = _read_exported_fields(contract_path)

        if pandera_fields != exported_fields:
            missing_in_export = sorted(set(pandera_fields) - set(exported_fields))
            missing_in_pandera = sorted(set(exported_fields) - set(pandera_fields))
            if missing_in_export:
                mismatches.append(
                    f"[{entity_name}] fields missing in exported contract: {missing_in_export}"
                )
            if missing_in_pandera:
                mismatches.append(
                    f"[{entity_name}] stale exported fields not in pandera: {missing_in_pandera}"
                )

            shared = sorted(set(pandera_fields) & set(exported_fields))
            for field_name in shared:
                if pandera_fields[field_name] != exported_fields[field_name]:
                    mismatches.append(
                        f"[{entity_name}] field '{field_name}' mismatch: "
                        f"pandera={pandera_fields[field_name]} exported={exported_fields[field_name]}"
                    )

    if mismatches:
        print("Gold contract parity check failed:")
        for item in mismatches:
            print(f"- {item}")
        return 1

    print("Gold contract parity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
