# RF-FS-003 Baseline Plan

**Дата:** 2026-03-19  
**Тема:** Восстановить явный test ownership и прямую связность source-to-test для приоритетных модулей  
**Связанные находки:** `FS-002`  
**Основной scope:** `tests/unit/` и mapping к `src/bioetl/application/core/`, `src/bioetl/application/composite/`, `src/bioetl/infrastructure/storage/`, `src/bioetl/infrastructure/adapters/`, частично `src/bioetl/domain/ports/`

## Цель

Цель `RF-FS-003` — не добиться формального 1:1 соответствия между каждым source-файлом и отдельным `test_<module>.py`. Такой подход дал бы красивую таблицу, но много шумовых тестов с низкой ценностью. Реальная задача — сделать ownership тестов явным для behavior-heavy модулей и устранить зоны, где у критичных файлов нет читаемого test owner. По baseline прямой naive mapping показывает сотни source-модулей без зеркального unit-теста. Это не означает, что код не покрыт. Во многих местах coverage clustered и построен разумно. Но именно файловая структура тестов перестала объяснять, какой тест “владеет” каким модулем, а это уже проблема поддержки, refactor cost и локального аудита.

## Что считается проблемой

Нужно разделять три случая. Первый — модуль действительно behavior-heavy, но у него нет ни прямого unit-теста, ни очевидного cluster-owner test file. Это настоящий долг. Второй — модуль покрыт косвенно, но это видно только после долгого чтения нескольких suites. Это уже не coverage issue, а ownership issue. Третий — модуль является чистым re-export/contract/marker/port facade и не нуждается в собственном `test_<module>.py`. Такой случай нельзя флагать как дефект только из-за отсутствия зеркального файла.

Именно поэтому `RF-FS-003` должен быть policy-driven, а не механическим.

## Приоритетные зоны

По текущему baseline сильнее всего страдают:
- `application/core`;
- `application/composite`;
- `infrastructure/storage`;
- behavior-heavy части `infrastructure/adapters`;
- selectively `domain/ports`.

У `domain/ports` особый статус. Большая часть таких модулей содержит Protocol/facade contracts. Им нужен не прямой unit-test на файл, а архитектурная и type-level верификация использования. Поэтому blanket mirror здесь ошибочен. В `infrastructure/adapters` ситуация обратная: многие файлы operationally significant, но покрытие часто распределено по provider suites и не всегда очевидно.

## Подход

Задача должна идти не от каталога тестов, а от классификации модулей.

### Категория A. Behavior-heavy modules

Сюда попадают orchestration services, runtime helpers, writer modules, planning/merge modules, storage builders и подобный код. Для них нужно одно из двух:
- прямой `test_<module>.py`;
- либо явная фиксация, какой existing suite выступает owner.

### Категория B. Shared helper clusters

Если тест покрывает не один файл, а целый helper cluster, это допустимо. Но тогда должна быть явная привязка: comment block, ownership note, manifest или именованный fixture-builder, из которого видно, какой cluster он валидирует.

### Категория C. Facades / Protocols / re-exports

Для них достаточно архитектурных тестов, import contract tests, `mypy`, иногда smoke tests. Создавать отдельные mirror-файлы ради структуры не нужно.

## Конкретные действия

1. Составить таблицу приоритетных source-модулей по пяти зонам и присвоить каждому статус: `direct_test`, `cluster_owner`, `arch_only`, `ignore`.
2. Для `application/core`, `application/composite` и `infrastructure/storage` закрывать сначала behavior-heavy лидеров.
3. В `infrastructure/adapters` идти по провайдерам и фиксировать ownership по provider suite, а не по каждой вспомогательной модели.
4. В `domain/ports` не плодить unit tests на Protocols, если достаточно `mypy` и architecture contract tests.
5. Для clustered suites при необходимости добавить краткие ownership comments, а не писать новые слабые тесты.

## Риски

Основной риск этой задачи — превратить её в статистическую кампанию. Если оптимизироваться под число mirror-файлов, репозиторий получит десятки бесполезных tests, которые проверяют trivial imports или очевидные dataclass поля. Второй риск — мешать test ownership cleanup с рефакторингом production-кода. Это разные задачи. Третий риск — ошибочно считать все пропуски одинаково важными. В `application/core` и `infrastructure/storage` отсутствие ясного owner хуже, чем в фасадном `domain/ports`.

## Минимизация рисков

- Ввести явную классификацию модулей до написания новых тестов.
- Начинать только с приоритетных cluster-heavy пакетов.
- Считать успехом не рост числа тестовых файлов, а уменьшение “ничьих” модулей.
- Для портов и фасадов полагаться на architecture tests, contract tests и `mypy`, а не на шумовые unit tests.

## Верификация

После каждого кластера:

```bash
./.venv/Scripts/python.exe -m pytest tests/unit/application/core -q
./.venv/Scripts/python.exe -m pytest tests/unit/application/composite -q
./.venv/Scripts/python.exe -m pytest tests/unit/infrastructure/storage -q
./.venv/Scripts/python.exe -m pytest tests/unit/infrastructure/adapters -q
```

Параллельно:

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
```

Для architecture-oriented ownership:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture -q
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

Если будет использоваться coverage-репорт, его нужно применять только к touched modules, а не как самоцель для всего проекта.

## Definition of Done

`RF-FS-003` можно считать завершённым, если:
- у behavior-heavy модулей в приоритетных кластерах есть читаемый test owner;
- clustered suites задокументированы там, где ownership неочевиден;
- `domain/ports` не зашумлены бессмысленными mirror-тестами;
- test structure объясняет ответственность лучше, чем на baseline;
- новые тесты повышают реальную диагностическую ценность, а не только файловую симметрию.

Итоговая цель этого RF — восстановить понятную связь между кодом и тестами как структурный контракт сопровождения, а не как формальную метрику покрытия.
