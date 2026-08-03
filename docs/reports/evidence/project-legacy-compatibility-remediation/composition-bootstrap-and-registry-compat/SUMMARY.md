# Сбор доказательств завершён: composition-bootstrap-and-registry-compat

**Создано объектов evidence:** 6
**Статус gate:** PASSED

## Краткий итог

| ID | Краткое утверждение | Confidence |
|----|----------------------|------------|
| EV-composition-entrypoints-is-curated-retained-public-facade | `composition.entrypoints` уже curated как retained public facade, а не как transient shim. | 0.98 |
| EV-composition-registry-remains-mixed-module-with-default-registry-compat | `composition.registry` остаётся mixed-module: canonical instance API плюс shared default-registry compatibility. | 0.96 |
| EV-composition-provider-package-root-and-loader-are-canonical-lifecycle-surface | Provider package root и `loader.py` выглядят как canonical lifecycle/bootstrap surface. | 0.94 |
| EV-composition-datasourcecreatorport-is-family-wide-terminology-compat-layer | `DataSourceCreatorPort` — family-wide terminology alias layer, а не одиночный leftover. | 0.93 |
| EV-composition-deprecated-pipeline-config-and-services-shims-are-measured-only | `config_resolution`, `configs`, `services.creation_api` уже measured-only deprecated shims. | 0.97 |
| EV-composition-pipeline-creation-api-is-sanctioned-support-seam-not-plain-deprecated-shim | `pipeline.creation_api` — sanctioned support seam, а не обычный deprecated shim. | 0.95 |

## Ключевые выводы

- В composition-family подтверждены как минимум четыре разные compatibility корзины:
  - `retain-as-contract`: `composition.entrypoints`, provider package root, `loader.py`;
  - `mixed-module / uncertain`: `composition.registry` + `registry_default`;
  - `retain-with-window`: `pipeline.config_resolution`, `pipeline.configs`, `services.creation_api`;
  - `sanctioned support seam`: `pipeline.creation_api`.
- Самые явные будущие removal candidates внутри shard — measured-only deprecated shims, а не public composition facades.
- `DataSourceCreatorPort` нужно рассматривать как coordinated terminology migration, а не как точечное удаление одного alias.

## Зафиксированные противоречия

- Часть composition-модулей внешне похожа на legacy barrels, но docs, freeze guards и boundary tests трактуют их как sanctioned public/bootstrap contract.
- `pipeline.creation_api` тоже выглядит как shim, но governance и tests отделяют его от truly deprecated warning-based aliases.

## Оставшиеся пробелы

- Нужна cross-shard проверка, не закрепляют ли `DataSourceCreatorPort` и default-registry seams дополнительные docs/config anchors вне composition family.
- Decision phase должен отдельно решить судьбу `composition.registry`: считать его `retain-with-window` или более долгоживущим `uncertain` mixed seam.
- Для measured-only shims нужна migration-window классификация: достаточно ли test-only retention, или нужен explicit removal milestone.
