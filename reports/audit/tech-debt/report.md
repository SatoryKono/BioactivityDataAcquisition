# Technical debt audit — `src/bioetl` (full, 2026-09-24)

| Field | Value |
| --- | --- |
| Date | 2026-09-24T10:03:04Z |
| Ref | working-tree `9d2992a9e402` (uncommitted changes present, incl. #10962/#10963 fixes) |
| SCOPE | `src/bioetl` |
| MODE | `audit` (read-only; no product edits in this cycle) |
| AUDIT_MODE | `full` |
| REQUIRE_GH_TRACKING | `false` (no new issues; #10962/#10963 already closed) |
| surface_score | **3** (debt identified with owner/risk/effort; new code does not worsen baseline) |

## Executive

Measured debt, не raw markers: **0** TODO/FIXME/HACK в `src/bioetl` (4 raw hits = DEPRECATED enum, CVCL_XXXX ×2, ADR-XXX — все FP).

Дельта к `tech-debt-src-20260923` (SCOPE=`src`, score 2): утренние находки закрыты в этом дереве — FK-трио 100% statements+branches (#10962), 3 `type: ignore` устранены (#10963). Бюджеты не повышены, exemptions 0.

## Trend vs registries

| Signal | 2026-09-23 | Now | Direction |
| --- | --- | --- | --- |
| `debt_scorecard` exemptions | 0 | 0 | held |
| FK trio coverage | 76.74/77.5/88.41 partial | 100/100/100 (focused suite) | improved |
| `type: ignore` в scope | ~20 | 17 pre-existing + 0 новых | improved |
| `pragma: no cover` | facades | facades, без снятия | held |
| `nosec` | registry/B105 | то же | held |
| composition 280/295 | watch | не перемерялся (F-004 GAP) | carry-over |

## Marker / suppression triage

| Class | Raw | Measured debt |
| --- | --- | --- |
| TODO/FIXME/HACK/XXX/WORKAROUND | 0 | none |
| DEPRECATED/CVCL_XXXX/ADR-XXX/TEMP | 4 + TEMP IDS/IRI | 0 (все FP) |
| `pragma: no cover` | ~25 | 0 — `__getattr__`-фасады и defensive paths; не снимать |
| `type: ignore` | 17 + 2 doc-FP | F-003 P3 watch: только mypy-gated `cast()` |
| `nosec` | ~30 | 0 — registry refs / B105 PASS-enum |

`coverage.xml` в checkout отсутствует — inventory-ребейз за штатным генератором.

## Findings (risk order)

| ID | P | Status | Claim |
| --- | --- | --- | --- |
| F-001 | P2 | PROVEN | FK-трио 100%; acceptance #10962 выполнен |
| F-002 | P3 | PROVEN | 2 HTTP-шва на `cast()`; acceptance #10963 выполнен |
| F-003 | P3 | PROVEN | 17 остаточных `type: ignore`; только поштучно под mypy |
| F-004 | P2 | NOT_PROVEN/GAP | composition headroom не перемерен; watch, no issue |

## Top-5 (probability × blast)

1. F-001 — inventory-ребейз FK-трио (генератор + coverage.xml).
2. F-003 — поштучные `ignore→cast()` (transformer_init, fallback mixin).
3. F-004 — перемер composition при следующем цикле.
4. Constructor waiver `QuarantineEntry` (expiry 2026-12-31) — carry-over.
5. CLI ~410 LOC вне hotspot families — carry-over.

## Stop

Бюджеты/exemptions не повышены. Ремедиаций с ростом лимитов нет — reject не понадобился.

## Checks

- `compile --domain tech-debt --profile audit-readonly` → OK
- `render prompt.audit.cycle (DOMAIN/SCOPE/MODE/AUDIT_MODE/LANGUAGE/REQUIRE_GH_TRACKING)` → OK
- marker scans `rg` (4 класса) → выходы выше
- findings.json contract (required keys, 64-hex fingerprints, статусы) → SCHEMA_OK, 4 findings

Skipped: `coverage.xml` EXCLUDED-map; `mypy --strict`; basedpyright; Sonar; полный inventory-ребейз (нужен coverage-конвейер).
Mirror-sync: N/A (в цикле нет правок `.codex`/`.junie`). `.env` не тронут.
