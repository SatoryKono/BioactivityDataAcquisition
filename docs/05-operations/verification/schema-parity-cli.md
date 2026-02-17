# Schema Parity CLI

`src/tools/verify_schema_parity.py` validates parity across:

- Domain dataclass entities (`bioetl.domain.entities.*`)
- Silver PyArrow schemas (`bioetl.infrastructure.schemas.silver`)
- Gold Pandera contracts (`bioetl.domain.contracts.gold`)

It compares:

1. Field names
1. Field types
1. Nullability
1. Field descriptions (when present in schema metadata)

## Usage

```bash
PYTHONPATH=src .venv/bin/python src/tools/verify_schema_parity.py
```

Write report to a custom path:

```bash
PYTHONPATH=src .venv/bin/python src/tools/verify_schema_parity.py \
  --report-path artifacts/schema-parity-report.json
```

Non-blocking mode (for exploratory runs):

```bash
PYTHONPATH=src .venv/bin/python src/tools/verify_schema_parity.py \
  --no-fail-on-mismatch
```

## CI machine-readable output

The tool always writes a JSON report (default: `artifacts/schema-parity-report.json`) with:

- Per-entity mismatch details
- Per-entity issue counts
- Top-level summary status (`pass` or `fail`)

Suggested CI pattern:

```bash
PYTHONPATH=src .venv/bin/python src/tools/verify_schema_parity.py \
  --report-path artifacts/schema-parity-report.json
```

Then publish `artifacts/schema-parity-report.json` as a CI artifact.

## Exit codes (blocking checks)

- `0`: No parity issues found, or run with `--no-fail-on-mismatch`.
- `1`: Parity issues found while blocking mode is enabled (default).

Recommended for blocking CI checks: **do not** pass `--no-fail-on-mismatch`.
