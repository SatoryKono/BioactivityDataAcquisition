# Архитектурные диаграммы

Актуальный код: основной вход — CLI (`bioetl.interfaces.cli`), оркестратор пайплайнов — `PipelineBase`/`ChemblPipelineBase` + `ChemblEntityPipeline`, запись — `UnifiedOutputWriter` с атомарной записью и checksum, обработка ошибок — `ErrorPolicyABC` (по умолчанию fail-fast с retry/skip через хуки), логирование — `UnifiedLogger`.

Политика и стили: см. `docs/architecture/diagrams/00-diagramming-policy.md` (обязательные шрифты 22/18 pt, нейтральная палитра, линии ≥1.5 px, единый layout). Перед PR убедитесь, что все диаграммы ниже соответствуют стилю; при изменениях обновляйте файлы.

## 1. High-Level Architecture (Hexagonal)

Диаграмма отображает архитектуру Ports & Adapters, где доменная логика (Core) изолирована от внешнего мира (Infrastructure/Interfaces).

Диаграмма: `docs/architecture/diagrams/flow/high-level-architecture.mmd`.

## 2. Pipeline Class Structure

Детальная диаграмма классов пайплайна и связанных сервисов.

Диаграмма: `docs/architecture/diagrams/class/pipeline-class-structure.mmd`.

## 3. Pipeline Execution Flow (Sequence)

Диаграмма последовательности выполнения метода `Pipeline.run()`.

Диаграмма: `docs/architecture/diagrams/sequence/pipeline-run-sequence.mmd`.

## 4. Execution Logic & Error Handling (Flowchart)

Логика управления потоком выполнения и обработки ошибок.

Диаграмма: `docs/architecture/diagrams/flow/pipeline-error-flowchart.mmd`.

## 5. Client Architecture (Three-Layer Pattern)

Реализация паттерна Contract -> Factory -> Implementation для внешних интеграций.

Диаграмма: `docs/architecture/diagrams/class/client-architecture-three-layer.mmd`.

## 6. Domain Services & Transform

Взаимодействие сервисов трансформации и валидации данных.

Диаграмма: `docs/architecture/diagrams/flow/domain-services-transform.mmd`.

## 7. Project Component Structure (Package Diagram)

Структура пакетов проекта и их зависимости, отражающие Clean Architecture.

Диаграмма: `docs/architecture/diagrams/flow/project-package-structure.mmd`.
