# SCHEMA-001: physical/logical schema parity evidence

Date: 2026-10-25. Issue: #12475. Status: **BLOCKED / NOT_VERIFIABLE**.

## Scope and provenance

This report restores the missing evidence document from PR #12532. It records
observations on Windows/PowerShell, not a reproduction of the original Jules
sandbox. Tested revision: `f29b3c0b2abf2f6ef07e114ac714672859eac23f`.
Checkout: `C:/BioactivityDataAcquisition/pr12503`.
Interpreter: `C:/BioactivityDataAcquisition/work/.venv-win/Scripts/python.exe`
(Python 3.13.7). Commands below used this interpreter, abbreviated as `<python>`.

Installed backend/library versions, read with `importlib.metadata.version`, match
this revision's `uv.lock`: deltalake 0.25.5, polars 2.0.0, pyarrow 25.0.1,
pandera 0.34.1. No dependency or parity baseline was updated.

## Layer formats: source declarations, not observed physical schemas

`configs/base/pipeline.yaml` declares these defaults:

| Layer | Declared default | What was physically verified |
| --- | --- | --- |
| Bronze | JSONL | No local dataset available; schema and serialization not measured |
| Silver | Delta, merge | No local Delta log/data available; types/nullability/evolution not measured |
| Gold | Delta, SCD2 | No local Delta log/data available; types/nullability/evolution not measured |

These are base defaults, not proof of each pipeline's resolved configuration or
an exhaustive backend inventory. Do not assume Bronze is Delta, or that every
deployment uses these local paths. CSV exports are not substituted for the
canonical table. Remote stores and credentials were not probed.

## Executed checks

All commands ran from the checkout above on the tested revision.

1. `Test-Path -LiteralPath data/output/bronze`, the equivalent Silver and Gold
   checks, and `Test-Path -LiteralPath data/output/silver/chembl/molecule` each
   returned `False` before the integrity probe. These are local absence checks,
   not evidence that data is missing from production or from another checkout.
2. `<python> -c 'import sys,importlib.metadata as m; print(sys.version.split()[0]); print({n:m.version(n) for n in ("deltalake","polars","pyarrow","pandera")})'`
   exited 0 and produced the versions recorded above.
3. `<python> scripts/ops/data/check_delta_integrity.py C:/BioactivityDataAcquisition/pr12503/data/output/silver/chembl/molecule`
   exited **1**:

   ```text
   Loading table: C:/BioactivityDataAcquisition/pr12503/data/output/silver/chembl/molecule
   ERROR: no log files
   ```

   The backend probe created an empty local target directory. A subsequent
   `Get-ChildItem -LiteralPath data/output/silver/chembl/molecule -Force -Recurse`
   returned no entries. No Delta transaction log, table, or data records were
   created. Directory existence after the probe is not table availability.
4. `<python> scripts/schema/validation/verify_schema_parity.py --help` exited 1
   with `ModuleNotFoundError: No module named 'scripts'`. The supported module
   invocation, `<python> -m scripts.schema.validation.verify_schema_parity --help`,
   exited 0. The direct-file invocation is not a schema finding.
5. `<python> -m scripts.schema.validation.verify_schema_parity --mode blocking`
   exited **0**: `No new blocking schema parity issues.` It also printed existing
   Silver-only-field warnings. This checker compares declared Silver/Gold
   contracts against its existing baseline; it does **not** read a real dataset,
   prove physical parity, or establish that every schema difference is absent.

## Acceptance gaps and required follow-up

- Physical write/read round trips on representative real backend objects:
  **NOT RUN**.
- Physical versus logical field types, nullability, and applicable evolution
  rules: **NOT_VERIFIABLE**.
- Controlled negative mismatch on a real temporary table/object: **NOT RUN**.
  A missing table is an availability failure, not the required negative parity test.
- Independent review and issue closeout: **OPEN**. No PASS, merge, deployment,
  or formal acceptance is claimed by this report.

The Stage 0 prerequisites #12457, #12458, and #12460 were OPEN when inspected.
Only evidence collection was performed; no parity implementation or CI parity
gate was introduced. After the applicable gate is cleared, identify resolved
formats per pipeline, provide an authorized representative fixture/store, run
write/read and negative-mismatch checks on pinned backend versions, and record
object identifiers, exact commands, exit codes, and schema comparisons. Keep
#12474 (implementation of CI checks) separate and downstream of #12475.
