"""REMOVED: Quarantine Explorer operator UI is no longer shipped.

Domain pipeline quarantine write/storage remains in BioETL.
This module is a fail-closed stub for old call sites
(`python -m scripts.ops ensure-quarantine-explorer`).
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    del argv
    print(
        "ensure-quarantine-explorer was removed: Quarantine Explorer UI is no longer shipped.",
        file=sys.stderr,
    )
    print(
        "Domain quarantine write-path is unchanged; only the operator Explorer/HTTP UI was deleted.",
        file=sys.stderr,
    )
    print(
        "For Grafana identity panels use: bioetl health server --port 8000 "
        "(BioETL Ops HTTP).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
