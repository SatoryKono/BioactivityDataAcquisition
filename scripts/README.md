# scripts — Canonical Script Surface

The `scripts/` root is intentionally compact.

## Root Policy

- Root directories are capped and domain-oriented.
- Root files are capped at three:
  - `README.md`
  - `catalog.yaml`
  - `run.py`
- Canonical logic lives in subpackages, not in root-level entrypoints.

## Root Directories

- `scripts/ai` — AI launchers, MCP tooling, and agent support.
- `scripts/data` — compatibility data facade.
- `scripts/diagrams` — diagram generation, linting, and render quality gates.
- `scripts/docs` — documentation build, drift checks, fixers, and matrix tooling.
- `scripts/engineering` — CI, dev, QA, diagnostics, baselines, and repo governance.
- `scripts/memory` — Neo4j-backed project memory utilities.
- `scripts/ops` — runtime, maintenance, observability, migration, and support tooling.
- `scripts/schema` — schema generation and validation contracts.

## Canonical Entry Points

Use grouped module entrypoints where available:

```bash
python -m scripts.run --help
python scripts/run.py --help

python -m scripts.docs --help
python -m scripts.engineering.qa --help
python -m scripts.engineering.repo --help
python -m scripts.engineering.dev --help
python -m scripts.ops --help
python -m scripts.memory --help
python -m scripts.diagrams --help
python -m scripts.schema --help
python -m scripts.ai --help
```

## Frequently Used Commands

```bash
python -m scripts.engineering.qa report-dep-map --check
python -m scripts.docs build-site --strict
python -m scripts.engineering.repo check-catalog --catalog scripts/catalog.yaml
python -m scripts.engineering.repo check-inventory --check --manifest configs/quality/scripts_inventory_manifest.json
python -m scripts.ops rerender-grafana
python -m scripts.engineering.dev migrate-deprecated-names src/
```

## Catalog

`scripts/catalog.yaml` is the governance manifest for canonical roots and group ownership.
If you add or relocate script domains, update the catalog and rerun the repo governance checks.

## Compatibility Policy

- Historical root-level wrappers have been consolidated into canonical domain packages.
- New integrations should target grouped module commands or canonical package paths only.
- Historical evidence under `docs/reports/evidence/**` may still mention removed paths; treat those references as archival, not canonical guidance.
