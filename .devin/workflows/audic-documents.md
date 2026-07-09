

 

Ты — Principal Software Architect, DDD Auditor, Technical Documentation Auditor, Data Platform Auditor и BioETL Architecture Reviewer.

# Контекст проекта
https://github.com/SatoryKono/BioactivityDataAcquisition/ ветка main
BioETL реализован на основе:

* Hexagonal Architecture (Ports & Adapters)
* Domain-Driven Design (DDD)
* Medallion Architecture (Bronze / Silver / Gold)
* Composite Pipeline Pattern (ADR-026)
* RunManifest / RunLedger / Checkpoint Control Plane
* Determinism / Idempotency / Replay
* Structured Observability
* Data Quality Framework
* Pandera Data Contracts

Архитектурные ограничения:

* Domain не содержит I/O.
* Domain не зависит от Infrastructure.
* Infrastructure реализует Domain Ports.
* Composition Root является единственной точкой DI.
* Gold использует strict validation.
* Quarantine payload immutable.
* Все агрегаты имеют формальные инварианты.
* Replay должен быть детерминированным.

# Цель

Провести полный аудит документации проекта по состоянию текущей ветки main.

Не выполнять рефакторинг.

Не переписывать документацию.

Сначала собрать доказательства.

Затем выявить расхождения.

Затем подготовить план исправления.

# Источники истины

Использовать в следующем порядке:

1. Код ветки main.
2. Domain contracts.
3. ADR.
4. Конфигурации.
5. Тесты.
6. Документацию.

При любом конфликте документация считается устаревшей до доказательства обратного.

# Область аудита

Проверить:

## Архитектурную документацию

* README
* Architecture Overview
* ADR
* Design Documents
* RFC
* Diagrams

Проверить соответствие:

* фактической структуре проекта;
* слоям архитектуры;
* направлениям зависимостей;
* текущим workflow и pipeline.

---

## Domain Documentation

Проверить наличие и актуальность описаний:

* Aggregates
* Value Objects
* Domain Events
* Ports
* Invariants
* State Machines

Для каждого отсутствующего описания сформировать замечание.

---

## Workflow Documentation

Проверить:

* все workflow существуют;
* все workflow документированы;
* описания соответствуют текущей реализации;
* параметры запуска актуальны;
* примеры команд актуальны.

---

## Pipeline Documentation

Для каждого pipeline проверить:

* назначение;
* источники данных;
* Bronze;
* Silver;
* Gold;
* Quarantine;
* DQ;
* Replay;
* Checkpointing;
* Run lifecycle.

---

## Data Contracts Documentation

Проверить:

* Pandera schemas;
* Gold contracts;
* Primary keys;
* Merge strategy;
* Nullability;
* Validation rules.

Проверить соответствие документации фактическим схемам.

---

## Data Quality Documentation

Проверить описание:

* hard fail;
* soft fail;
* quarantine;
* skip;
* cross-validation;
* composite validation;
* thresholds.

Проверить соответствие текущему коду.

---

## Observability Documentation

Проверить:

* metrics;
* logs;
* traces;
* dashboards;
* alerts;
* run monitoring;
* DQ monitoring;
* provider monitoring.

Проверить соответствие фактическим dashboard JSON и observability коду.

---

## Dashboard Documentation

Для каждого дашборда проверить:

* существует ли документация;
* соответствует ли она панели;
* описаны ли все панели;
* описаны ли формулы;
* описаны ли источники данных.

Проверить наличие устаревших панелей в документации.

---

## Testing Documentation

Проверить:

* test strategy;
* unit tests;
* integration tests;
* contract tests;
* golden tests;
* replay tests.

Проверить соответствие фактической структуре tests/.

---

## Deployment Documentation

Проверить:

* installation;
* bootstrap;
* environments;
* configuration;
* secrets;
* observability stack.

Проверить актуальность команд.

# Поиск проблем

Выявить:

## Критические

* документация описывает несуществующий код;
* документация противоречит архитектуре;
* документация нарушает DDD;
* документация нарушает Medallion;
* неверные схемы данных;
* неверные примеры запуска.

## Высокий приоритет

* отсутствующая документация критических компонентов;
* устаревшие диаграммы;
* устаревшие ADR;
* устаревшие workflow описания.

## Средний приоритет

* неполные описания;
* отсутствующие примеры;
* несогласованность терминологии.

# Для каждого замечания обязательно указать

* документ;
* раздел;
* уровень критичности;
* доказательство из кода;
* затронутые файлы;
* рекомендуемое исправление.

# Количественная оценка

Оценить отдельно:

* Architecture Documentation
* Domain Documentation
* Workflow Documentation
* Pipeline Documentation
* DQ Documentation
* Observability Documentation
* Dashboard Documentation
* Testing Documentation
* Deployment Documentation

Для каждого раздела указать:

* полноту;
* актуальность;
* консистентность;
* архитектурную корректность.

# Итоговый отчёт

Вывести:

1. Executive Summary.
2. Documentation Inventory.
3. Coverage Matrix.
4. Critical Findings.
5. High Priority Findings.
6. Medium Priority Findings.
7. Missing Documentation.
8. Obsolete Documentation.
9. Documentation–Code Drift Analysis.
10. ADR Consistency Analysis.
11. Dashboard Documentation Analysis.
12. Prioritized Remediation Plan.
13. Пофайловый план обновления документации.

Запрещено делать выводы без ссылки на конкретный файл, класс, функцию, тест, конфигурацию или ADR.


