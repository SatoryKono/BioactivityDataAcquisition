from __future__ import annotations

import importlib


def step(name: str) -> None:
    print(f"IMPORT {name}...", flush=True)
    importlib.import_module(name)
    print(f"OK {name}", flush=True)


def main() -> int:
    modules = [
        "bioetl.domain.exceptions.base",
        "bioetl.domain.types.enums",
        "bioetl.domain.types.identifiers",
        "bioetl.domain.types.health",
        "bioetl.domain.types.gold_contracts",
        "bioetl.domain.types.gold_schema_policy",
        "bioetl.domain.types_config_validation",
        "bioetl.domain.types",
        "bioetl.domain.exceptions.data_quality",
    ]
    for module in modules:
        step(module)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
