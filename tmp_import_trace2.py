from __future__ import annotations

import importlib


def step(name: str) -> None:
    print(f"IMPORT {name}...", flush=True)
    importlib.import_module(name)
    print(f"OK {name}", flush=True)


def main() -> int:
    modules = [
        "tests.helpers.clock",
        "tests.helpers.vcr_config",
        "tests.e2e.conftest",
        "httpx",
        "pytest",
        "deltalake.exceptions",
        "vcr.errors",
        "bioetl.domain.exceptions.data_quality",
        "bioetl.domain.exceptions.infrastructure",
        "bioetl.domain.exceptions.network",
        "tests.e2e.test_pipeline_matrix_e2e",
    ]
    for module in modules:
        step(module)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
