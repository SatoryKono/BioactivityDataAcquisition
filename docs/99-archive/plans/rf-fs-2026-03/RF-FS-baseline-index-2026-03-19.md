# RF-FS Baseline Index

**Дата:** 2026-03-19  
**Серия:** `RF-FS-001 .. RF-FS-007`  
**Назначение:** единая точка входа в baseline-планы по рефакторингу файловой структуры BioETL

## Состав серии

1. [RF-FS-001-baseline-2026-03-19.md](./RF-FS-001-baseline-2026-03-19.md)  
   Разрыв циклов в `composition` и соседних runtime-кластерах.

2. [RF-FS-002-baseline-2026-03-19.md](./RF-FS-002-baseline-2026-03-19.md)  
   Сужение самых широких flat-пакетов: `application/core`, `application/composite`, `infrastructure/storage`, `interfaces/cli/commands`.

3. [RF-FS-003-baseline-2026-03-19.md](./RF-FS-003-baseline-2026-03-19.md)  
   Восстановление явного test ownership без механического 1:1 mirror-подхода.

4. [RF-FS-004-baseline-2026-03-19.md](./RF-FS-004-baseline-2026-03-19.md)  
   Нормализация topology конфигурации между `configs`, `domain`, `infrastructure`, `composition`.

5. [RF-FS-005-baseline-2026-03-19.md](./RF-FS-005-baseline-2026-03-19.md)  
   Доведение split semantic hotspots: `cli_run_orchestration_service` и `application/pipelines/chembl/_pipelines.py`.

6. [RF-FS-006-baseline-2026-03-19.md](./RF-FS-006-baseline-2026-03-19.md)  
   Подтверждение и cleanup orphan/wrapper candidates, включая metadata wrapper chain.

7. [RF-FS-007-baseline-2026-03-19.md](./RF-FS-007-baseline-2026-03-19.md)  
   Формализация контракта структуры `infrastructure/adapters/{provider}`.

## Краткая карта зависимостей

Серия не линейна полностью, но зависимости достаточно выражены.

- `RF-FS-005` лучше начинать первым. Это самый локальный и дешёвый structural win. Он уже частично начат в CLI-кластере и даёт быстрый выигрыш без тяжёлого graph churn.
- `RF-FS-001` должен идти раньше `RF-FS-004`, потому что часть циклов в `composition` завязана на config wiring. Если сначала трогать topology конфигурации, те же файлы могут быть передвинуты дважды.
- `RF-FS-004` разумно запускать только после устранения крупных composition cycles.
- `RF-FS-006` нужно ставить после `RF-FS-001` и `RF-FS-004`, потому что часть orphan/wrapper candidates может либо исчезнуть, либо стать понятнее только после cleanup циклов и ownership config concerns.
- `RF-FS-002` лучше делать уже после cycle/config cleanup. Широкие package-splits не должны происходить поверх нестабильной import topology.
- `RF-FS-003` лучше ближе к концу, когда package geography и ownership модулей уже стабилизированы. Иначе test ownership придётся чинить повторно после move-wave.
- `RF-FS-007` можно вести поздно и отдельно как governance/contract wave. Он почти не блокирует остальные RF.

В сжатом виде DAG выглядит так:

```text
RF-FS-005
   -> RF-FS-001
   -> RF-FS-004
   -> RF-FS-006
   -> RF-FS-002
   -> RF-FS-003

RF-FS-007
   -> mostly independent
   -> best after structural stabilization
```

## Рекомендуемый порядок исполнения

Практический порядок на несколько итераций:

1. `RF-FS-005a`  
   Довести уже начатый split вокруг CLI orchestration.

2. `RF-FS-005b`  
   Разобрать ChEMBL `_pipelines.py`.

3. `RF-FS-001a`  
   Разорвать цикл в `composition/providers` и `composition/factories/datasource`.

4. `RF-FS-001b`  
   Разорвать цикл в `composition/factories/pipeline` и `composition/factories/services`.

5. `RF-FS-001c`  
   Добить малые циклы в `application` и `infrastructure`.

6. `RF-FS-004`  
   Нормализовать config topology после стабилизации composition graph.

7. `RF-FS-006a`  
   Подтвердить статусы orphan/wrapper candidates.

8. `RF-FS-006b`  
   Выполнить delete/merge/retain cleanup только по подтверждённым кандидатам.

9. `RF-FS-002a..d`  
   Разбивать широкие пакеты по одному кластеру за батч.

10. `RF-FS-003`  
    Вернуть явный test ownership для приоритетных модулей.

11. `RF-FS-007`  
    Зафиксировать adapter package contract и привести architecture test к реальному правилу.

## Приоритеты

### Приоритет 1

- `RF-FS-001`
- `RF-FS-004`

Это архитектурные блокеры. Они влияют на import graph, ownership конфигурации и предсказуемость composition/runtime wiring.

### Приоритет 2

- `RF-FS-005`
- `RF-FS-006`
- `RF-FS-002`

Это структурные улучшения с высоким возвратом, но они безопаснее после стабилизации основных зависимостей.

### Приоритет 3

- `RF-FS-003`
- `RF-FS-007`

Они важны для долгосрочной поддерживаемости и governance, но меньше блокируют непосредственные refactor-wave.

## Общий verify-подход

Для всей серии стоит держать единые правила:

- После каждого батча запускать tests и `check_doc_links.py --configs` параллельно.
- После всех import rewiring, package moves и boundary changes обязательно гонять architecture tests.
- После structural refactor-wave гонять `mypy --strict --no-incremental`.
- Не смешивать в одном батче package move и изменение поведения без веской причины.
- Compatibility re-exports не удалять в тот же момент, когда делается первичный split.

Базовые команды:

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
./.venv/Scripts/python.exe -m pytest tests/architecture -q
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

К ним добавляются cluster-local suites для каждого RF.

## Общие критерии готовности серии

Серию `RF-FS-*` можно считать выполненной качественно только если одновременно достигнуты следующие эффекты:

- import graph в composition больше не содержит крупных циклов;
- ownership конфигурации по слоям читается однозначно;
- package structure перестаёт быть плоской и шумной в ключевых hotspots;
- orphan/wrapper candidates либо удалены, либо получили явный статус;
- test ownership стал понятнее для behavior-heavy модулей;
- adapter package contract зафиксирован архитектурно корректно;
- все изменения прошли architecture checks, unit/integration suites и строгую типизацию.

## Примечание по текущему состоянию

На дату этого индекса `RF-FS-005a` уже частично реализован: `cli_run_orchestration_service` был облегчён через вынос моделей и контрактов в отдельные owner-модули, а связанные CLI helpers уже переведены на canonical imports. Это не закрывает всю серию, но делает `RF-FS-005` правильной стартовой точкой для продолжения.
