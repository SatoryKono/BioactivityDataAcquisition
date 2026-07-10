# Сбор доказательств завершён: infrastructure-adapters-and-fallbacks

**Создано объектов evidence:** 8
**Статус gate:** PASSED

## Краткий итог

| ID | Краткое утверждение | Confidence |
|----|----------------------|------------|
| EV-infrastructure-config-package-root-is-curated-retained-config-facade | `bioetl.infrastructure.config` уже выступает как curated retained config facade. | 0.98 |
| EV-infrastructure-storage-package-root-and-delta-alias-are-test-facing-compat-surface | `bioetl.infrastructure.storage` и alias `delta` держат test/tool-facing compatibility surface. | 0.95 |
| EV-infrastructure-noop-validator-aliases-are-bounded-retain-with-window-seam | `NoOpSilverValidator` / `NoOpGoldValidator` — bounded compatibility aliases с явным future-retirement профилем. | 0.96 |
| EV-infrastructure-dq-contract-loader-keeps-legacy-dq-files-as-migration-bridge | `DQContractConfigLoader` держит старые DQ YAML как migration bridge, а не как dead fallback. | 0.94 |
| EV-infrastructure-source-normalizer-remains-active-legacy-shape-bridge | `source_normalizers.source` остаётся active bridge между legacy/new config shapes. | 0.95 |
| EV-infrastructure-retired-source-pagination-aliases-already-moved-to-rejection-guard | Часть старых pagination aliases уже не сохраняется, а переведена в reject-guards. | 0.97 |
| EV-infrastructure-metadatawriter-facade-preserves-historical-monkeypatch-contract | `MetadataWriter` facade удерживается historical monkeypatch/test contract. | 0.96 |
| EV-infrastructure-adapter-fallback-helpers-are-active-resilience-behavior-not-legacy-cleanup-target | Adapter fallback helpers нельзя автоматически считать legacy debt. | 0.93 |

## Ключевые выводы

- В infrastructure-family confirmed как минимум пять разных корзин:
  - `retain-as-contract`: `infrastructure.config`, `metadata_writer` facade;
  - `retain-with-window`: `NoOpSilverValidator`, `NoOpGoldValidator`;
  - `migration-bridge`: `DQContractConfigLoader`, `source_normalizers.source`;
  - `already-retired`: pagination aliases, переведённые в reject-guards;
  - `exclusion / active behavior`: adapter resilience fallback helpers.
- Самые реалистичные будущие removal candidates внутри shard — validator aliases, но только после migration of tests/importers.
- Самая большая ошибка, которую здесь нужно избежать на decision-stage: смешать runtime resilience fallback-и с backward-compat cleanup backlog.

## Зафиксированные противоречия

- `source_normalizers.source` одновременно содержит legacy/new-shape bridge и explicit retirement enforcement; весь family нельзя целиком пометить одной меткой `retain` или `remove`.
- Package-root `config` и `storage` визуально похожи на barrels, но docs/comments/tests делают их sanctioned compatibility/public surfaces.
- Наличие слова `fallback` в infrastructure не означает, что модуль существует ради старого поведения; часть fallback helpers — текущая product capability.

## Оставшиеся пробелы

- Нужна cross-shard проверка, не удерживают ли config/docs ещё дополнительные импортные anchors для validator aliases и storage delta patch paths.
- Decision phase должна развести `migration-bridge` и `retain-with-window`: у DQ/source normalization эти окна, вероятно, будут длиннее, чем у validator aliases.
- Стоит отдельно проверить, не есть ли ещё скрытые legacy kwargs/path seams в `bronze_writer.py` и `silver_writer.py`, которые лучше классифицировать вместе с config/storage compatibility work.
