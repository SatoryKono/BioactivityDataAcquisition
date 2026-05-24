from __future__ import annotations

import importlib
import sys


def step(name: str) -> None:
    print(f"IMPORT {name}...", flush=True)
    importlib.import_module(name)
    print(f"OK {name}", flush=True)


def main() -> int:
    modules = [
        "tests.helpers.clock",
        "tests.helpers.vcr_config",
        "tests.e2e.conftest",
        "tests.e2e.test_pipeline_matrix_e2e",
        "tests.e2e.test_e2e_stability_policy",
    ]
    for module in modules:
        step(module)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
