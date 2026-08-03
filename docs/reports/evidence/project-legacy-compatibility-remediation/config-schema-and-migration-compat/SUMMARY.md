# Сбор доказательств завершён: config-schema-and-migration-compat

**Создано объектов evidence:** 6
**Статус gate:** PASSED

## Краткий итог

| ID | Краткое утверждение | Confidence |
|----|----------------------|------------|
| EV-config-ci-contract-is-the-normative-ledger-for-active-retired-and-transitional-keys | `config_ci_contract.py` — единый policy ledger для active/retired/transitional config keys. | 0.98 |
| EV-config-filter-batch-size-is-an-explicit-transitional-alias | `filter_batch_size` — явный transitional alias с `deprecated=True`, а не canonical field. | 0.97 |
| EV-config-retired-file-reference-keys-are-already-outside-the-active-contract | Ряд legacy file-reference keys уже официально вышел из active contract. | 0.96 |
| EV-config-rules-make-legacy-field-support-explicitly-time-boxed | RULES задаёт time-boxed migration semantics для legacy field support. | 0.98 |
| EV-config-naming-exceptions-yaml-is-a-curated-legacy-decision-registry | `naming_exceptions.yaml` — curated decision registry по legacy/compat exceptions. | 0.95 |
| EV-config-entity-alias-policy-is-an-intentional-contract-projection | Entity alias policies и field-alias registries часто являются intentional contract projection. | 0.94 |
| EV-config-runtime-normalizers-still-bridge-selected-old-shapes | Runtime normalizers всё ещё поддерживают selected old config shapes. | 0.95 |

## Ключевые выводы

- Config family уже управляется явной governance-моделью:
  - `retired`: legacy file-reference keys и path fragments;
  - `transitional`: `filter_batch_size` и похожие time-boxed aliases;
  - `migration-bridge`: runtime normalizers и schema alias bridges;
  - `retain-as-contract`: stable pipeline IDs и entity alias projections, закреплённые policy/data contracts.
- Самые чистые будущие removal candidates внутри shard — explicit transitional fields, а не вся alias/normalization family целиком.
- Config compatibility в BioETL нельзя оценивать только по runtime code: policy уже живёт в `RULES`, `configs/README`, `config_ci_contract.py` и `naming_exceptions.yaml`.

## Зафиксированные противоречия

- Config layer одновременно запрещает часть legacy names и сохраняет другие как audited exceptions; broad “remove all aliases” стратегия здесь заведомо неверна.
- Runtime normalizers всё ещё нужны для части old shapes, но рядом уже есть alias categories, которые официально переведены в retired bucket.
- Aliases в entity configs внешне выглядят как historical clutter, но data contracts показывают, что часть из них intentional и layer-specific.

## Оставшиеся пробелы

- Decision phase должна отдельно классифицировать runtime normalizers: какие из них tied to current migration windows, а какие уже можно готовить к retire-with-proof.
- Нужен cross-shard join с domain/application pack, чтобы отделить config-level legacy field policy от code-level compatibility constructors.
- Стоит отдельно проверить, есть ли внешние operator/docs consumers у `filter_batch_size`, помимо schema/policy retention.
