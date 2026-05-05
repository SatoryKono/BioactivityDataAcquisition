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


def extract_pubchem_property_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed = {key: set() for key in URN_KEYS}
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            for prop in payload.get("props", []):
                urn = prop.get("urn") or {}
                if not isinstance(urn, dict):
                    continue
                for key in URN_KEYS:
                    value = urn.get(key)
                    if value is not None:
                        observed[key].add(str(value))
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
