# Сводка evidence-wave: project-legacy-compatibility-remediation

- Дата: `2026-03-29`
- Статус: `completed`
- Режим: `full`

## Цель

Собрать актуальную доказательную базу по deprecated, legacy,
compatibility-only и backward-compatible code surface в BioETL, а затем
превратить подтверждённые retirement candidates и retained contracts в явные
решения по удалению, сохранению или отложенной миграции.

## Текущее состояние

- Parent pillar создан и готов к shard-level evidence collection.
- Выполнен initial keyword/inventory baseline по `deprecated`, `legacy`,
  `compat`, `shim`, `fallback`, `alias`.
- Уже на kickoff-уровне видно, что тема не сводится к одному слою:
  существенные сигналы есть в `interfaces`, `composition`, `infrastructure`,
  `configs`, `docs`, `tests` и governance inventory.

## Shards

- `interfaces-cli-and-public-entrypoint-compat`
- `composition-bootstrap-and-registry-compat`
- `domain-application-legacy-seams`
- `infrastructure-adapters-and-fallbacks`
- `config-schema-and-migration-compat`
- `tests-docs-and-governance-anchors`

## Статус gate

- Parent gate: `PASSED`
- Child shard gates:
  - `interfaces-cli-and-public-entrypoint-compat`: `PASSED` (`6/5`)
  - `composition-bootstrap-and-registry-compat`: `PASSED` (`6/5`)
  - `domain-application-legacy-seams`: `PASSED` (`6/5`)
  - `infrastructure-adapters-and-fallbacks`: `PASSED` (`8/5`)
  - `config-schema-and-migration-compat`: `PASSED` (`7/5`)
  - `tests-docs-and-governance-anchors`: `PASSED` (`6/5`)

## Итоговые артефакты

- `03-synthesis/CROSS-SYNTHESIS-project-legacy-compatibility-remediation.md`
- `04-decisions/DECISIONS.yaml`
- `05-risks/RISKS.yaml`
- `06-status/keyword-scan-2026-03-28.md`
- `LEGACY-REMOVAL-EXECUTION-PLAN.md`

## Ранние выводы

- В репо уже есть curated compatibility inventory и governance-history, так что
  значительная часть compatibility surface вероятно intentional и требует
  decision-based retirement, а не механического удаления.
- `interfaces/cli` и `composition/*` выглядят как зоны с высокой плотностью
  public compatibility seams и re-export shielding.
- Третий завершённый shard (`composition-bootstrap-and-registry-compat`)
  подтвердил, что composition нельзя описывать одной меткой `legacy`: внутри
  семьи одновременно живут retained public façades, mixed registry contracts,
  measured-only deprecated shims и sanctioned support seams.
- Четвёртый завершённый shard (`domain-application-legacy-seams`) показал,
  что здесь главный split проходит между retained package-root contracts и
  маленькими legacy helpers: широкие domain/application facades в основном
  остаются контрактными, а реальными retirement candidates становятся узкие
  compatibility constructors и time-boxed helper APIs.
- Пятый завершённый shard (`infrastructure-adapters-and-fallbacks`) показал,
  что infrastructure нельзя описать как единый legacy bucket: внутри family
  одновременно живут retained package-root facades, test-facing monkeypatch
  seams, bounded validator aliases, migration bridges для config shapes и уже
  завершённые retirement guards.
- Второй завершённый shard (`interfaces-cli-and-public-entrypoint-compat`)
  подтвердил, что CLI layer уже распадается на две разные compatibility
  корзины: top-level public wrappers как `retain-as-contract` и helper/policy
  seams как measured-only или `retain-with-window`.
- `infrastructure/*fallback*` действительно требует отдельного shard-level
  решения: часть fallback helpers — active resilience behavior и не должна
  автоматически попадать в cleanup backlog.
- Шестой завершённый shard (`config-schema-and-migration-compat`) подтвердил,
  что config compatibility уже управляется явной policy-системой: active /
  retired / transitional ключи закреплены централизованно, а alias removal
  в этой зоне должен следовать governance windows, а не только code cleanup.
- В `configs` и `RULES.md` уже описаны migration windows, alias policies и
  transitional compatibility markers; это потенциальные blockers для premature
  removal.
- Первый завершённый shard (`tests-docs-and-governance-anchors`) подтвердил,
  что tests/docs/governance образуют отдельный contract layer: многие seams
  будут классифицироваться не как `retire-now`, а как `retain-as-contract` или
  `retain-with-window`.

## Ближайшие шаги

1. Синтезировать shard-level findings в одну parent-level compatibility map.
2. Зафиксировать не только removal candidates, но и contractual compatibility
   surfaces, которые блокируют premature cleanup.
3. После parent synthesis оформить решения в классификацию:
   `retire-now | retain-with-window | retain-as-contract | uncertain`.

## Финальный статус

- Все 6 child shard gates закрыты.
- Parent cross-synthesis создан.
- Decision ledger и risk ledger созданы.
- Сформирован staged execution plan для будущих removal waves.

## Execution Progress

- `Wave 0` выполнен: import inventory и gating для first-wave removal candidates собраны в ходе removal slices.
- `Wave 1` завершена: composition shims, legacy validation constructors, validator aliases и CLI alias-only cluster уже удалены.
- `Wave 2` закрыта как inventory-first и narrowed-cleanup волна для `retain-with-window` и `migration-bridge` seams.
- Стартовый shortlist `Wave 2` зафиксирован в `06-status/wave-2-shortlist-2026-03-29.md`.
- Для `Wave 2` создан migration-bridge ledger с owner/review/exit criteria:
  `06-status/wave-2-migration-bridge-ledger-2026-03-29.md`.
- Выполнен targeted inventory pass по `DQContractConfigLoader`; этот bridge теперь выглядит как лучший кандидат на narrowed `Wave 2` cleanup без удаления public loader surface.
- Narrowed `Wave 2` cleanup по `DQContractConfigLoader` уже выполнен: legacy DQ file fallback удалён, а public contract-based loader surface оставлен.
- Выполнен targeted inventory pass по `pipeline_normalizers.py` и `source_normalizers/source.py`; оба модуля подтверждены как active bridges, а не ready-to-remove legacy seams.
- Отдельный readiness pass по `filter_batch_size` показал, что alias уже не удерживается repo-local sample configs, но всё ещё встроен в first-party runtime model и resolver path; поэтому governance-only retirement пока блокирован.
- `Wave 3` зафиксирована на текущей границе: `filter_batch_size` сознательно исключён из текущего refactoring scope, а по `pipeline_normalizers.py` и `source_normalizers/source.py` выполнены первые narrowing slices без перехода в более широкий refactor.
