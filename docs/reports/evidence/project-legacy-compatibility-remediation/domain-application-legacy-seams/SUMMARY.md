# Сбор доказательств завершён: domain-application-legacy-seams

**Создано объектов evidence:** 6
**Статус gate:** PASSED

## Краткий итог

| ID | Краткое утверждение | Confidence |
|----|----------------------|------------|
| EV-domain-filtering-package-root-is-retained-backcompat-facade | `bioetl.domain.filtering` остаётся retained backwards-compatible package-root facade. | 0.97 |
| EV-domain-exceptions-package-root-remains-cross-layer-compat-surface | `bioetl.domain.exceptions` — сильная cross-layer compatibility surface. | 0.98 |
| EV-domain-validation-compat-constructors-are-test-retained-legacy-helpers | Legacy validation constructors удерживаются в основном test coverage. | 0.94 |
| EV-application-shutdown-request-wait-remain-backcompat-test-facing-seam | `ShutdownService.request()/wait()` всё ещё живы как backward-compatible seam. | 0.95 |
| EV-application-metricsservererror-reexport-is-cross-layer-compat-contract | Re-export `MetricsServerError` — cross-layer compatibility contract. | 0.96 |
| EV-domain-pubmed-alias-fields-remain-config-and-doc-anchored | PubMed alias-поля уже закреплены configs/docs и не выглядят как simple leftovers. | 0.93 |

## Ключевые выводы

- В `domain/application` основные compatibility seams делятся не по слоям, а по форме контракта:
  - `retain-as-contract`: package-root re-exports и cross-layer exception surfaces;
  - `retain-with-window`: старые API methods и helper aliases;
  - `future retirement candidate`: legacy constructors с почти нулевым runtime usage.
- Самый чистый candidate на следующий removal/migration pass здесь — legacy validation constructors, а не широкие package-root facades.
- Alias-поля в publication family уже перешли из “legacy hints” в downstream config/schema contract и требуют migration proof перед любым cleanup.

## Зафиксированные противоречия

- Многие seams выглядят как backward-compat leftovers, но на практике удерживаются не только кодом, а ещё tests, docs и user-facing schema references.
- Наиболее “старые” helpers в shard не обязательно самые опасные: package-root re-exports старее, но они контрактные; узкие constructors моложе по риску и ближе к реальному retirement backlog.

## Оставшиеся пробелы

- Нужна cross-shard проверка, не закрепляют ли publication alias fields дополнительные anchors в config migration policy и data-contract governance.
- Decision phase должен решить, считать ли `ShutdownService.request()/wait()` долгоживущим compatibility API или time-boxed seam.
- Полезно отдельно проверить, есть ли внешние consumers legacy validation constructors вне repo-wide first-party usage.
