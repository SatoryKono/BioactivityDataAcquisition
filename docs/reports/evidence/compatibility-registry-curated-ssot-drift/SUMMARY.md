# Сводка evidence: compatibility-registry-curated-ssot-drift

Дата: 2026-03-21
Статус: завершено

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Примечание о rebaseline: the current repo state still matches the current-state reading in this pack; no new evidence objects were needed to preserve the trigger-vs-baseline distinction.

## Текущая интерпретация

This shard now serves primarily as historical trigger evidence for why the compatibility-registry refactor was opened.

- The evidence objects remain valid as records of the pre-alignment pressure points.
- The current repo baseline has already addressed the largest SSOT gap through:
  - `configs/quality/compatibility_facade_inventory.yaml`
  - `scripts/engineering/ci/_compatibility_registry.py`
  - `scripts/engineering/qa/generate_compatibility_facade_snapshot.py`
- Freeze guards should now be read more narrowly: they are mostly import-discipline and removal-policy guardrails, not a second curated registry that should be migrated wholesale.

## Созданные объекты evidence

- `EV-compatibility-registry-curated-ssot-drift-inventory-doc-exposes-curated-and-measured-ledgers`
- `EV-compatibility-registry-curated-ssot-drift-test-hardcodes-retained-entrypoint-path-set`
- `EV-compatibility-registry-curated-ssot-drift-test-builds-measured-registry-from-docstring-prefixes`
- `EV-compatibility-registry-curated-ssot-drift-telemetry-script-hardcodes-tracked-docstring-prefixes`
- `EV-compatibility-registry-curated-ssot-drift-telemetry-reporting-test-replays-inventory-counts`
- `EV-compatibility-registry-curated-ssot-drift-freeze-guards-hardcode-separate-compatibility-allowlists`

## Проверка gate

Minimum evidence required: `5`

Collected: `6`

Статус gate: `PASSED`

## Сводка evidence

| ID                                                                                                    | Claim Summary                                                                        | Confidence |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------- |
| EV-compatibility-registry-curated-ssot-drift-inventory-doc-exposes-curated-and-measured-ledgers       | Inventory doc now mixes curated ledger and measured registry snapshot                | 0.97       |
| EV-compatibility-registry-curated-ssot-drift-test-hardcodes-retained-entrypoint-path-set              | Inventory test hardcodes retained-entrypoint paths and duplicates the ledger in code | 0.96       |
| EV-compatibility-registry-curated-ssot-drift-test-builds-measured-registry-from-docstring-prefixes    | Inventory test synthesizes a measured registry from docstring prefixes               | 0.95       |
| EV-compatibility-registry-curated-ssot-drift-telemetry-script-hardcodes-tracked-docstring-prefixes    | CI telemetry hardcodes tracked prefixes and builds its own snapshot logic            | 0.95       |
| EV-compatibility-registry-curated-ssot-drift-telemetry-reporting-test-replays-inventory-counts        | Telemetry reporting test replays inventory counts and status totals                  | 0.94       |
| EV-compatibility-registry-curated-ssot-drift-freeze-guards-hardcode-separate-compatibility-allowlists | Freeze guards carry separate hand-maintained allowlists for compatibility policy     | 0.93       |

## Ключевые выводы

- At collection time, the compatibility inventory was acting as both curated ledger and measured report, which justified splitting manual and generated surfaces.
- At collection time, tests and telemetry still looked registry-like enough to justify a YAML-centered refactor direction.
- In the current repo state, the remaining freeze-guard duplication signal is best treated as a narrow calibration concern, not as justification for a broad second migration wave.

## Gaps

- This pack captures the highest-signal current duplication points, but it does not enumerate every compatibility-related allowlist in the repo.
- `configs/quality/source_test_facade_inventory.yaml` is a precedent-only reference and was not turned into a separate evidence object.
