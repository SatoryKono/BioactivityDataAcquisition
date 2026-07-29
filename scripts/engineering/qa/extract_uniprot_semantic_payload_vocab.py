"""Extract observed UniProt semantic payload vocabularies from Bronze fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _iter_jsonl_payloads(paths: list[Path]) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payloads.append(json.loads(line))
    return payloads


def _collect_field_values(
    items: object,
    *,
    field_name: str,
) -> set[str]:
    values: set[str] = set()
    if not isinstance(items, list):
        return values
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(field_name)
        if value is not None:
            values.add(str(value))
    return values


def extract_uniprot_semantic_payload_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed: dict[str, set[str]] = {
        "feature_types": set(),
        "comment_types": set(),
        "keyword_categories": set(),
    }
    for payload in _iter_jsonl_payloads(paths):
        observed["feature_types"].update(
            _collect_field_values(payload.get("features", []), field_name="type")
        )
        observed["comment_types"].update(
            _collect_field_values(payload.get("comments", []), field_name="commentType")
        )
        observed["keyword_categories"].update(
            _collect_field_values(payload.get("keywords", []), field_name="category")
        )
    return {key: sorted(values) for key, values in observed.items() if values}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    payload = extract_uniprot_semantic_payload_vocab(list(args.paths))
    rendered = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
    if args.json_out is None:
        print(rendered)
    else:
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
