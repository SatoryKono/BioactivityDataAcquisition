# Сводка evidence: project-documentation-drift

Дата: 2026-03-26
Статус: ребейзлайнено под текущий documentation baseline

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Примечание о follow-up: после `RF-011` verify-sensitive documentation surfaces
тоже были повторно подтверждены на актуальном дереве. Это не снимает
documentation debt, но переводит parent pack из режима broad freshness concern
в режим calibrated residual drift.

Примечание о 2026-03-26 cleanup wave: tracked merged export был убран из
default git-surface и переведён в generated-on-demand policy. Это не закрывает
весь derivative lag, но переводит `operations-generated-doc-drift` из режима
`committed stale export` в режим `on-demand/generated surface governance`.

## Shard-пакеты

1. [project-and-ai-doc-drift](../project-and-ai-doc-drift/SUMMARY.md) — `6` объектов evidence, gate `PASSED`
1. [architecture-doc-drift](../architecture-doc-drift/SUMMARY.md) — `5` объектов evidence, gate `PASSED`
1. [reference-guide-doc-drift](../reference-guide-doc-drift/SUMMARY.md) — `5` объектов evidence, gate `PASSED`
1. [operations-generated-doc-drift](../operations-generated-doc-drift/SUMMARY.md) — `6` объектов evidence, gate `PASSED`

## Итоги

- Объектов evidence в rebaselined shard packs: `22`
- Rebaselined shard-ов: `4/4`
- Статус parent gate: `PASSED`

## Текущее состояние

- Выборочно исправленные active-source areas в `project-and-ai-doc-drift` и `reference-guide-doc-drift` теперь являются current baseline, а не still-open remediation queue.
- Самый сильный оставшийся active debt остаётся в `architecture-doc-drift`, где проблема заключается в snapshot undercount и omissions, а не в нарушении архитектурных правил.
- `operations-generated-doc-drift` остаётся derivative-surface lag pack: после cleanup wave он больше не описывает постоянно закоммиченный merged export, а концентрируется на on-demand exports, generated maps и historical verification artifacts.
- Generated verify-sensitive artifacts вроде dependency map и compatibility snapshot сейчас свежие и зелёные; оставшийся documentation debt сосредоточен в interpretation, labeling и active-source coverage gaps.
