# Сбор evidence завершён: compatibility-registry-policy-history-mixing

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

**Создано объектов evidence:** 7
**Gate Статус:** PASSED

Примечание о rebaseline: the repo still reflects the same measured-only governance and history-splitting conclusions captured here, so the pack remains a valid current-state reference.

## Текущая интерпретация

This shard now reads best as historical trigger evidence plus policy context.

- The key ambiguity it captured was real: measured-only governance existed, but the promotion rule was not explicit enough.
- That ambiguity is now reduced in the current repo state because measured-only rows carry machine-readable policy fields in the YAML SSOT.
- The historical-narrative mixing problem is also reduced because review history now lives outside the operational ledger.

## Сводка evidence

| ID                                                                                   | Claim Summary                                                                                                        | Confidence |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- | ---------- |
| EV-compatibility-registry-policy-history-mixing-measured-only-baseline               | The inventory reports 5 measured-only modules outside the curated ledger and 0 transition-debt rows.                 | 0.96       |
| EV-compatibility-registry-policy-history-mixing-telemetry-prefix-gating              | Telemetry decides measured membership by inventory rows plus docstring-prefix tracking.                              | 0.90       |
| EV-compatibility-registry-policy-history-mixing-test-enforces-measured-registry      | Tests enforce measured-path equality and measured-only counts as a CI contract.                                      | 0.97       |
| EV-compatibility-registry-policy-history-mixing-inventory-contains-review-wave       | The inventory contains a dated review-wave section inside the operational ledger.                                    | 0.93       |
| EV-compatibility-registry-policy-history-mixing-composition-doc-defers-governance    | Composition guidance defers compatibility status back to the inventory.                                              | 0.92       |
| EV-compatibility-registry-policy-history-mixing-quality-config-ownership-model       | The quality config reserves compatibility facades for contract/architecture ownership.                               | 0.88       |
| EV-compatibility-registry-policy-history-mixing-registry-pattern-mixed-module-policy | The registry-pattern guide separates compatibility states and mixed-module policy for future compatibility surfaces. | 0.89       |

## Key Observations

- At collection time, the inventory was measurable, but the measured-only set was only visible as a count unless readers cross-checked the telemetry/test contract.
- At collection time, historical review narrative was embedded directly inside the operational inventory, so the document acted as both ledger and review log.
- The underlying governance-distribution signal remains useful, but the current baseline is clearer than it was when this shard was collected.

## Отмеченные противоречия

- The inventory was described as curated, not exhaustive, while the telemetry/test contract still demanded full measured-path equality.
- The same document that served as the live compatibility ledger also contained dated review-wave narrative, which mixed current policy and historical review context.

## Оставшиеся пробелы

- This pack records evidence only; it does not choose a preferred policy interpretation or propose a remediation path.
- The current scan focused on the requested primary sources and their immediate policy neighbors.
- Future compatibility modules still need disciplined operational classification, but the repo now has a stronger baseline through measured-only policy fields in the YAML SSOT.
