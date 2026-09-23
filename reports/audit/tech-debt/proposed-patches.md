# Proposed patches (operator MODE=propose-patches)

Budget/exemption increases: **rejected**. Only shrink or rebind.

## Patch A — AUD-001 rebind (apply in this branch)

```text
python scripts/engineering/qa/report_architecture_quality_scorecard.py
python -m scripts.engineering.qa report-architecture-debt-remote-main-baseline --update
# LF-normalize JSON if the writer emits CRLF
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
```

Do **not** copy hashes by hand. Do **not** raise scorecard weights or composition cap.

## Patch B — AUD-002 split `_core.py` (do not apply here; XL)

Sequential extractions, each PR &lt;500 LOC net new files, keep public CLI entry:

1. `sync_pkg/cli_parser.py` — argparse surface
2. `sync_pkg/http_backend.py` — `http.client` / urllib
3. `sync_pkg/ast_probes.py` — ast scanners
4. `sync_pkg/neo4j_statements.py` — Cypher builders
5. Leave a thin `_core.py` facade until importers migrate

Gate: loc(`_core.py`) monotonic down; no xenon/complexity budget raise.
Reopen #10526 until loc &lt; 500.

## Patch C — AUD-004 FK coverage (separate test PR)

Add unit tests targeting missing lines in:

- `workflow_foreign_key_reconciliation_loaded.py` (10)
- `workflow_foreign_key_reconciliation_normalization.py` (9)
- `workflow_foreign_key_reconciliation_reads.py` (8)

Refresh inventory only via hash-preserving `--allow-missing-coverage-xml` plus
trusted coverage-verify XML. Never delete `pragma: no cover` to “gain” coverage.

## Patch D — AUD-005 mixin `cast()` (optional, mypy-gated)

Replace `type: ignore[arg-type]` in `transformer_initialization.py:47` and
`fallback_policy_mixin.py:116` with `cast(...)` mirroring
`openalex/_client_runtime_request.py`. Verify:

```text
mypy --strict <touched files>
pytest tests/unit/application/pipelines/common tests/unit/infrastructure/adapters/common -q
```

## Patch E — comment sync (optional S)

`configs/quality/package_cohesion_budget.yaml`: `live 279` → `live 280`.
Not a budget change.
