## Parent

#9639. Связано, но не дубль: #9624 (содержимое ADR matrix / integral coherence).

## Факт (verify-architecture full, 2026-08-25)

Каскад падений из невалидных/устаревших generated artifacts:

- `reports/quality/debt-governance-gates.json` на прогоне: `JSONDecodeError` (line 429) — closeout-тесты `#5518`–`#6169` не парсят payload.
- `source-tree-manifest.json` `source_tree_sha256=8877ea31…` ≠ live `dfe552f0…`.
- `module-coverage-inventory.json` хеш не совпадает с манифестом; 7 тестов skipped из‑за грязного артефакта.
- Stale: domain-ports inventory, architecture-quality-scorecard, observability cardinality evidence, test-governance-current, test-telemetry baseline, dead-code inventory, documentation-cleanup-inventory.

## Цель

Артефакты валидный JSON, hash-current, `--check` зелёный. **Не** менять формулы scorecard и **не** поднимать бюджеты.

## Правки

```text
python -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml
python -m scripts.engineering.qa report-source-tree-manifest
python -m scripts.engineering.qa report-domain-ports-inventory
python scripts/engineering/qa/report_architecture_quality_scorecard.py
python -m scripts.engineering.qa report-debt-governance-gates --update
python -m scripts.engineering.qa.refresh_governance_artifacts
```

Плюс точечно: observability cardinality evidence, test-governance collector, telemetry baseline (см. сообщения упавших тестов).

Содержимое ADR-058/059 в matrix — зона #9624; здесь только чтобы JSON парсился и hashes совпадали.

## Definition of Done

- `python -m json.tool reports/quality/debt-governance-gates.json` успешен.
- `report-module-coverage --check --allow-missing-coverage-xml` и `report-source-tree-manifest --check` зелёные.
- Closeout-тесты больше не падают на `JSONDecodeError`.
- Ни один debt `max_*` / hotspot cap не вырос.
