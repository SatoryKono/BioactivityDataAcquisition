"""Extract observed PubChem raw property-URN vocabulary from Bronze fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

URN_KEYS = (
    "datatype",
    "label",
    "name",
    "implementation",
    "software",
    "source",
    "release",
)


def _iter_jsonl_payloads(paths: list[Path]) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payloads.append(json.loads(line))
    return payloads


def _iter_pubchem_urns(payload: dict[str, object]) -> list[dict[str, object]]:
    urns: list[dict[str, object]] = []
    for prop in payload.get("props", []):
        if not isinstance(prop, dict):
            continue
        urn = prop.get("urn") or {}
        if isinstance(urn, dict):
            urns.append(urn)
    return urns


def _collect_urn_values(
    observed: dict[str, set[str]],
    *,
    urn: dict[str, object],
) -> None:
    for key in URN_KEYS:
        value = urn.get(key)
        if value is not None:
            observed[key].add(str(value))


def extract_pubchem_property_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed = {key: set() for key in URN_KEYS}
    for payload in _iter_jsonl_payloads(paths):
        for urn in _iter_pubchem_urns(payload):
            _collect_urn_values(observed, urn=urn)
    return {key: sorted(values) for key, values in observed.items() if values}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    payload = extract_pubchem_property_vocab(list(args.paths))
    rendered = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
    if args.json_out is None:
        print(rendered)
    else:
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
