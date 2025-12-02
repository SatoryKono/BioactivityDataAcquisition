# 03 Glossary

- **Assay** — описание биологического эксперимента; детали полей и схем см. `docs/architecture/01-domain-objects.md`.
- **Activity** — запись о результатах эксперимента с бизнес-ключом и хешами; подробности в `docs/architecture/01-domain-objects.md` и `docs/reference/schemas/00-schemas-overview.md`.
- **Target** — биологическая мишень, связанная с Assay/Activity; см. `docs/architecture/01-domain-objects.md`.
- **TestItem** — тестируемый объект (соединение, препарат), см. `docs/architecture/01-domain-objects.md`.
- **Pipeline** — инстанс `PipelineBase`, реализующий цепочку extract → transform → validate → write.
- **Stage** — этап пайплайна (extract/transform/validate/write) с отдельной ответственностью.
- **RunResult** — агрегированное состояние выполнения пайплайна, включая счётчики, метаданные и пути артефактов.
- **StageDescriptor** — описание параметров и источников для конкретной стадии (например, дескриптор ChEMBL выборки).
- **PipelineHook** — реализация `PipelineHookABC`, подключаемая к prepare_run/finalize_run.
- **ErrorPolicy** — стратегия обработки ошибок валидации или IO, определяет поведение при отклонениях данных.
- **SchemaRegistry** — сервис регистрации и выдачи Pandera-схем по доменным сущностям.
- **ValidationService** — обёртка над валидаторами, применяющая схемы и собирающая результаты.
- **UnifiedAPIClient** — фасад доступа к внешним API с ретраями, лимитами и кэшированием.
- **UnifiedOutputWriter** — единый интерфейс записи таблиц, метаданных и QC-отчётов с атомарностью.
