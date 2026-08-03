# Сбор доказательств завершён: tests-docs-and-governance-anchors

**Создано объектов evidence:** 6
**Статус gate:** PASSED

## Краткий итог

| ID | Краткое утверждение | Confidence |
|----|----------------------|------------|
| EV-governance-curated-registry-separates-zero-transition-debt-from-retained-entrypoints | Curated compatibility registry уже отделяет zero transition debt от retained public entrypoints. | 0.95 |
| EV-governance-retained-entrypoints-are-review-driven-not-auto-delete | Retained entrypoints управляются review dates и freeze rules, а не automatic deletion. | 0.96 |
| EV-history-current-cycle-forbids-deprecation-of-retained-adapter-entrypoints | Historical review уже запрещает deprecation retained adapter entrypoints в текущем цикле. | 0.94 |
| EV-test-ownership-inventory-makes-facade-tests-part-of-compat-contract | Facade/compat seams owned through contract tests, so removal требует test-ownership migration. | 0.92 |
| EV-rules-canonical-pk-policy-makes-legacy-aliases-time-bound-migration-only | RULES ограничивают legacy PK aliases переходным окном и fixed migration sequence. | 0.95 |
| EV-naming-registry-forbids-domain-legacy-aliases-without-explicit-window | Naming registry запрещает возврат старых domain aliases без explicit time-bound decision. | 0.94 |

## Ключевые выводы

- Tests/docs/governance в этой теме — не вторичный фон, а отдельный contract layer, который прямо ограничивает темп legacy cleanup.
- Важная первая развилка decision phase будет не между `delete / keep`, а между `retain-as-contract`, `retain-with-window` и `retire-now`.
- Retained entrypoints уже governed и для части из них deprecation в текущем цикле прямо заблокирован historical review.
- Migration windows и test ownership нужно рассматривать как обязательные removal blockers раньше любых кодовых удалений.

## Зафиксированные противоречия

- С одной стороны, governance настаивает на bounded migration windows и eventual alias retirement.
- С другой стороны, curated inventory и history прямо закрепляют группу retained entrypoints, которые сейчас не считаются transition debt и не подлежат немедленному удалению.

## Оставшиеся пробелы

- Пока не проверено, насколько фактические import/call-site inventories в `src/tests/scripts` совпадают с declared allowed call sites.
- Отдельно не исследованы docs-only legacy references, которые могут уже не соответствовать текущему runtime/governance posture.
- Требуется cross-shard сверка: какие code-level candidates реально блокируются этими governance anchors, а какие только кажутся защищёнными.
