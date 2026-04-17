# Сводка evidence: compatibility-registry-refactor

Дата: 2026-03-23
Статус: завершено

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.


Примечание о rebaseline: parent refactor posture по-прежнему соответствует текущему состоянию репозитория; выводы остаются откалиброванными под модель `YAML-ledger + generated snapshot`.

Примечание о follow-up: после `RF-011` compatibility snapshot `--check`
дополнительно подтверждён на актуальном дереве, поэтому parent pack теперь
фиксирует не просто реализованную миграцию, а свежий зелёный baseline.

## Shard-пакеты

1. [compatibility-registry-curated-ssot-drift](../compatibility-registry-curated-ssot-drift/SUMMARY.md) — `6` объектов evidence, gate `PASSED`, synthesis `complete`
2. [compatibility-registry-snapshot-automation-drift](../compatibility-registry-snapshot-automation-drift/SUMMARY.md) — `5` объектов evidence, gate `PASSED`, synthesis `complete`
3. [compatibility-registry-policy-history-mixing](../compatibility-registry-policy-history-mixing/SUMMARY.md) — `7` объектов evidence, gate `PASSED`, synthesis `complete`

## Итоги

- Объектов evidence в shard packs: `18`
- Завершённых shard-ов: `3/3`
- Статус parent gate: `PASSED`

## Главные выводы

- Исходное evidence правильно зафиксировало distributed ownership pressure, но текущее состояние репозитория уже включает реальный YAML SSOT, shared loader и generated snapshot tooling.
- Оставшийся duplication risk уже уже, чем казалось сначала: freeze guards в основном кодируют import-discipline и removal policy, а не второй curated registry, который надо wholesale мигрировать в YAML ledger.
- Inventory doc и snapshot companion теперь заметно лучше разделены, поэтому оставшаяся работа — это calibration и policy tightening, а не greenfield registry extraction.
- Measured-only governance была главным unfinished policy seam; теперь этот seam частично формализован через machine-readable поля `new_code_policy` и `promotion_trigger`.

## Актуализация текущего состояния

- `configs/quality/compatibility_facade_inventory.yaml` уже является структурированным compatibility ledger.
- `scripts/engineering/ci/_compatibility_registry.py` уже выступает shared loader contract.
- `scripts/engineering/qa/generate_compatibility_facade_snapshot.py` уже владеет generated measured snapshot flow.
- compatibility snapshot generation/check после `RF-011` остаётся зелёным на текущем дереве.
- Оставшаяся работа по `CR-02` должна оставаться узкой: извлекать из guardrails только registry-owned semantics там, где есть явный duplication win; не пытаться мигрировать все freeze-guard allowlists в shared loader.
