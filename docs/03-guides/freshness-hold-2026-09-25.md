______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-09-25'

______________________________________________________________________

# Freshness hold 2026-09-25

Documents below were read against the current tree on 2026-09-25.
Their `Last verified` dates stay unchanged because a concrete claim does not match the code.
Documents in the same age slice whose claims matched were stamped `2026-09-25` only after that check.
`.mmd` files are outside this slice: they have no `Last verified` header.

| Path | Reason |
| --- | --- |
| `docs/00-project/ai/agents/policy/agent-orchestration-rules.md` | Slash-команды /architecture-guardian, /new-composite, /config-validate, /schema-parity, /provider-health и /migration в runtime-деревьях отсутствуют. |
| `docs/00-project/ai/memory/neo4j-project-memory-seed.md` | Источники истины ссылаются на отсутствующие knowledge-graph JSON и SYN-project-package-topology.md. |
| `docs/00-project/ai/rules/RULES_COVERAGE_MATRIX.md` | §7.1 матрицы не совпадает с RULES.md v6.1.11 (там двойная верификация, не schema evolution). |
| `docs/00-project/ai/skills/README.md` | Указаны отсутствующие .codex/skills/documentation-cascade-audit и docs/00-project/ai/skills/global/. |
| `docs/00-project/ai/skills/SKILLS-PRACTICAL-INDEX.md` | Таблицы всё ещё вызывают снятые grafana-dashboard-extension и prometheus-metric-discovery. |
| `docs/00-project/glossary.md` | LoadingStrategy не содержит WATERMARK-BASED; модуля pandera_compat нет. |
| `docs/00-project/governance/03-file-policy.md` | Документ требует отсутствующий make validate-configs и старую форму sort_by.columns. |
| `docs/00-project/governance/07-doc-nav-policy.md` | Политика требует docs/05-engineering в primary nav, а mkdocs.yml исключает этот префикс. |
| `docs/02-architecture/07-compatibility-facade-inventory.md` | Разрешённый test path tests/unit/composition/test_services_entrypoints.py отсутствует. |
| `docs/02-architecture/decisions/ADR-004-pydantic-vs-dataclasses.md` | Решение требует Pydantic для всех моделей, PipelineConfig остаётся dataclass. |
| `docs/02-architecture/decisions/ADR-006-logger-metrics-ports.md` | Образец называет PipelineServices, класс называется PipelineService. |
| `docs/02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md` | Lifecycle описан на PipelineServices, живой класс PipelineService. |
| `docs/02-architecture/decisions/ADR-016-error-handling-strategy.md` | Образец импортирует CriticalPipelineError, класс называется CriticalError. |
| `docs/02-architecture/decisions/ADR-017-observability-architecture.md` | Путь composition/observability_api.py устарел. |
| `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md` | GoldValidator/gold_validator.py не совпадают с PanderaGoldValidator. |
| `docs/02-architecture/decisions/ADR-019-observability-port-enforcement.md` | Реализация привязана к отсутствующим interfaces/orchestration/signals.py. |
| `docs/02-architecture/decisions/ADR-020-basepipeline-decomposition.md` | Список файлов включает отсутствующие domain/config.py и lifecycle/lock_manager.py. |
| `docs/02-architecture/decisions/ADR-021-ddd-aggregates-adoption.md` | Указан отсутствующий _quarantine_entry_transitions_mixin.py. |
| `docs/02-architecture/decisions/ADR-022-tracing-noop.md` | NoOpTracing импортируется не из того модуля. |
| `docs/02-architecture/decisions/ADR-023-entity-type-patterns.md` | Ссылка на отсутствующий docs/audits/entity_type-audit.md. |
| `docs/02-architecture/decisions/ADR-024-entity-naming-unification.md` | Пути docs/glossary.md и configs/naming-exceptions.yaml отсутствуют. |
| `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md` | Класс назван EnrichmentCoordinator, в коде EnrichmentCoordinatorService. |
| `docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md` | Ссылка на отсутствующий src/bioetl/domain/config.py. |
| `docs/02-architecture/decisions/ADR-028-filter-rules-externalization.md` | Точка интеграции config_loader.py отсутствует. |
| `docs/02-architecture/decisions/ADR-029-output-metadata-unification.md` | Указанные metadata_coordinator.py и metadata_builder.py отсутствуют. |
| `docs/02-architecture/decisions/ADR-030-publication-pagination-strategy.md` | Implementation указывает отсутствующие фабрики и domain/config.py. |
| `docs/02-architecture/decisions/ADR-031-loading-strategy-formalization.md` | Implementation указывает отсутствующие services_factory.py и pipeline_factory.py. |
| `docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md` | Иерархия configs/validation/pubmed/publication.yaml отсутствует. |
| `docs/02-architecture/decisions/ADR-037-canonical-schema-generation.md` | Экспортер указан в src/tools, файл лежит в scripts/schema/generation/. |
| `docs/02-architecture/decisions/ADR-039-unified-entity-config-format.md` | config_loader.py как orchestration-модуль отсутствует. |
| `docs/02-architecture/diagrams/descriptions/architecture/03-medallion-data-flow.md` | Узлы CircuitBreaker/RateLimiter/TokenBucket не совпадают с классами Guard/RateLimiter. |
| `docs/02-architecture/diagrams/descriptions/architecture/06-storage-layer.md` | Текущим портом назван отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/architecture/06a-storage-writers.md` | Текущим портом назван отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/architecture/08b-composite-execution.md` | Узел PreflightValidator не совпадает с CompositePreflightValidationService. |
| `docs/02-architecture/diagrams/descriptions/architecture/10-resilience-patterns.md` | Узел CircuitBreaker не совпадает с CircuitBreakerGuard. |
| `docs/02-architecture/diagrams/descriptions/architecture/13-port-protocol-contracts.md` | Текущим портом назван отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/architecture/13a-data-storage-ports.md` | Текущим портом назван отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/architecture/13f-operational-ports-infra.md` | Узел LocalCheckpoint не совпадает с LocalCheckpointAdapter. |
| `docs/02-architecture/diagrams/descriptions/architecture/13h-port-contracts-storage.md` | Текущим портом назван отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/architecture/15-batch-executor-internals.md` | Названы отсутствующие PipelineProcessingPort и BatchStateCommitPort. |
| `docs/02-architecture/diagrams/descriptions/architecture/16b-transformer-pub-other.md` | Имена трансформеров не совпадают с *PublicationTransformer. |
| `docs/02-architecture/diagrams/descriptions/architecture/18b-checkpoint-shutdown.md` | Узел LocalCheckpoint не совпадает с LocalCheckpointAdapter. |
| `docs/02-architecture/diagrams/descriptions/architecture/21-idempotent-processing-guards.md` | CheckpointLoadService и CompositeRunner не совпадают с текущими классами. |
| `docs/02-architecture/diagrams/descriptions/architecture/43-uniprot-mapping-job-to-protein-fetch-enrichment.md` | Узел UniProtIdMappingClient отсутствует, клиент называется UniProtAdapter. |
| `docs/02-architecture/diagrams/descriptions/class-summary.md` | Сводка называет отсутствующие StoragePort, PublicationBase и coordinator-классы без суффикса Service. |
| `docs/02-architecture/diagrams/descriptions/class/01-domain-ports.md` | Список портов включает отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/class/02-entities-aggregates.md` | Ключевой элемент PublicationBase, в коде PublicationBaseSchema. |
| `docs/02-architecture/diagrams/descriptions/class/12-composite-pipeline.md` | Имена coordinator-классов в коде имеют суффикс Service. |
| `docs/02-architecture/diagrams/descriptions/foundation/06-pipeline-execution.md` | Среди текущих участников указан отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/foundation/24-hash-service-class.md` | Класса ContentHashService в src нет. |
| `docs/02-architecture/diagrams/descriptions/foundation/26-hexagonal-ports-adapters.md` | Среди портов указан отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/foundation/30-port-adapter-mapping.md` | Среди портов указан отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/foundation/35-bootstrap-sequence.md` | Класса ConfigLoader нет. |
| `docs/02-architecture/diagrams/descriptions/foundation/39-medallion-invariants.md` | Пути domain/types.py и application/services/medallion_lifecycle.py устарели. |
| `docs/02-architecture/diagrams/descriptions/views/01-full-system-component-domain.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/01-full-system-component-infra.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/04-domain-layer-class-diagram-infra.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/06-application-layer-class-diagram-infra.md` | Класса RunnerDependencies нет, контракт называется PipelineRunnerDependencies. |
| `docs/02-architecture/diagrams/descriptions/views/10-infrastructure-layer-class-diagram-dataflow.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/10-infrastructure-layer-class-diagram-domain.md` | Узлы StoragePort и RetryPolicy отсутствуют. |
| `docs/02-architecture/diagrams/descriptions/views/10-infrastructure-layer-class-diagram-infra.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/10-infrastructure-layer-class-diagram-overview.md` | Узлы StoragePort и RetryPolicy отсутствуют. |
| `docs/02-architecture/diagrams/descriptions/views/26-hexagonal-ports-adapters-dataflow.md` | Узлы StoragePort и PubchemAdapter неверны. |
| `docs/02-architecture/diagrams/descriptions/views/26-hexagonal-ports-adapters-domain.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/26-hexagonal-ports-adapters-full.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/26-hexagonal-ports-adapters-infra.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/26-hexagonal-ports-adapters-overview.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/28-composition-root-di-graph-overview.md` | Класса LoggerFactory нет. |
| `docs/02-architecture/diagrams/descriptions/views/30-port-adapter-mapping-full.md` | Рядом с живыми портами указан отсутствующий StoragePort. |
| `docs/02-architecture/diagrams/descriptions/views/35-bootstrap-sequence-full.md` | Узел ConfigLoader.load неверен. |
| `docs/02-architecture/diagrams/descriptions/views/36-architecture-principles-mindmap-domain.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/36-architecture-principles-mindmap-infra.md` | Узел StoragePort не соответствует узким storage-портам. |
| `docs/02-architecture/diagrams/descriptions/views/39-medallion-invariants-full.md` | Повторяет снятые пути domain/types.py и medallion_lifecycle.py. |
| `docs/02-architecture/diagrams/descriptions/views/48-composite-phase-lifecycle-infra.md` | Класса PhaseDispatcher нет. |
| `docs/02-architecture/diagrams/governance/PROMPT-diagram-expansion.md` | Раздел 0.4 требует читать снятые пути pipeline-run.py и batch-executor.py. |
| `docs/02-architecture/diagrams/governance/diagram-views-inventory.md` | Счётчик .mermaid и список семейств не совпадают с деревом. |
| `docs/02-architecture/diagrams/governance/diagram-views-plan.md` | Родительские пути названы .mermaid, канон лежит как .mmd. |
| `docs/02-architecture/diagrams/guide/architecture-reference.md` | Класса OTELTracer нет, трейсер называется OpenTelemetryTracer. |
| `docs/02-architecture/history/compatibility-facade-review-history.md` | publication_field_groups.py всё ещё помечен retained, модуля нет. |
| `docs/02-architecture/module-consolidation-migration-requirements.md` | Стартовый путь domain/value-objects неверен, пакет называется value_objects. |
| `docs/02-architecture/system-context.md` | В адаптерах назван ChemblClient, класс называется ChemblAdapter. |
| `docs/03-guides/add-new-source.md` | Регистрация описана через custom_creator, в ProviderConfig поле называется adapter_creator. |
| `docs/03-guides/add-pipeline-existing-source.md` | Процедура пишет в register_all_transformers и PIPELINE_CONFIGS, сейчас это manifest-модули. |
| `docs/03-guides/cleanup-policy.md` | .junie описан как полностью untracked, agents и skills отслеживаются. |
| `docs/03-guides/dashboards/dashboard-extension-llm.md` | Текст говорит о восьми shipped-страницах, в grafana/dashboards семь JSON. |
| `docs/03-guides/dashboards/dashboard-v2-usage.md` | Описан отсутствующий дашборд bioetl-workflow-overview. |
| `docs/03-guides/dashboards/v3.0/1-overview.md` | Handoff-номера не совпадают с navigation-links.yaml. |
| `docs/03-guides/dashboards/v3.0/template/README.md` | Ссылки на dashboard-requirements-comprehensive.md и dashboard-audit-checklist.md не резолвятся в guides. |
| `docs/03-guides/dashboards/v3.0/template/panel-contract.md` | Контракт всё ещё требует Explore-ссылки from/to после удаления Explore. |
| `docs/03-guides/dashboards/v3.0/template/run-centric-dashboard-template.md` | Шина 0..5 не совпадает с текущим bus 0..6. |
| `docs/03-guides/dashboards/v3.0/template/selector-resolution-contract.md` | Запрет видимого run_id противоречит bioetl-overview-v2.json. |
| `docs/03-guides/date-handling.md` | Цитируется отсутствующий src/bioetl/domain/normalization.py. |
| `docs/03-guides/development/codex-wsl2-setup.md` | wsl_proxy.py и start-wsl-proxy.bat указаны в scripts/ops/, файлы лежат в scripts/ops/runtime/wsl/. |
| `docs/03-guides/development/config-schema-guidelines.md` | Импорт DQConfig и InputFilterConfig из pipeline_config не существует. |
| `docs/03-guides/development/mistral-vibe-wsl2-setup.md` | Репозиторий не поставляет .vibe/config.toml. |
| `docs/03-guides/pipeline-lifecycle.md` | Утверждение про 15 модулей в application/composite/ не совпадает с деревом. |
| `docs/03-guides/publication-validation-guide.md` | Цитируется xlsx-схема, в дереве есть только csv. |
| `docs/03-guides/replay-guide.md` | Команда run-historical-replay-closure-campaign не зарегистрирована. |
| `docs/03-guides/workflows.md` | Путь workflow_runner_service.py устарел; класс лежит в application/services/workflow/. |
| `docs/04-reference/api/application.md` | Package exports сервисов сняты, перечисленные классы отсутствуют. |
| `docs/04-reference/api/application/services.md` | services/__init__.py оставил пустой __all__. |
| `docs/04-reference/api/composition.md` | Названы отсутствующие runtime-модули и классы CrossrefAdapterFactory/PipelineContractValidator. |
| `docs/04-reference/api/index.md` | Бюджет cross_layer_group_edges_total 334 не совпадает с 330 в коде. |
| `docs/04-reference/api/infrastructure.md` | CircuitBreaker и TokenBucket не совпадают с CircuitBreakerGuard и TokenBucketRateLimiter. |
| `docs/04-reference/components/config-runtime-artifacts.md` | get_config_drift и ConfigDriftReport в src отсутствуют. |
| `docs/04-reference/contracts/canonical-field-registry.md` | Артефакты аудита 2026-05-15 указаны как текущие, их нет в reports/. |
| `docs/04-reference/domain/control-plane.md` | Названы отсутствующие RunManifestArtifact и классы RunLedger/WorkflowLedger. |
| `docs/04-reference/domain/ports.md` | Каталог утверждает 74 файла, в domain/ports их 81. |
| `docs/04-reference/domain/symbol-invariant-traceability.md` | События BatchCompleted и QuarantineResolved отсутствуют. |
| `docs/04-reference/domain/value-objects.md` | Каталог неполон: нет orcid.py и export_identity.py. |
| `docs/04-reference/hash-policy.md` | Путь tests/unit/domain/hash-policy/ неверен, ключи YAML другие. |
| `docs/04-reference/pipelines/chembl/02-cell-line-spec.md` | Entity назван cell-line, YAML задаёт cell_line. |
| `docs/04-reference/pipelines/chembl/08-assay-parameters-spec.md` | Текущим Gold назван v1.0, registry держит 2.0.0. |
| `docs/04-reference/pipelines/chembl/12-publication-similarity-spec.md` | Текущим экспортом назван v1.0, опубликован только 2.0.0. |
| `docs/04-reference/pipelines/chembl/14-subcellular-fraction-spec.md` | Ключ entity_id не совпадает с YAML subcellular_fraction. |
| `docs/04-reference/pipelines/contract-facet-matrix.md` | Счётчики required/nullable не совпадают с contract-coverage-matrix.json. |
| `docs/04-reference/providers/chembl/activity.md` | Версия схемы 1.2.0, активный контракт 1.0.0. |
| `docs/04-reference/providers/chembl/assay-parameters.md` | Схема 1.2.0 и partition type не совпадают с 2.0.0 и parameter_type. |
| `docs/04-reference/providers/chembl/cell-line.md` | Версия схемы 1.2.0, активный контракт 1.0.0. |
| `docs/04-reference/providers/chembl/compound-record.md` | Версия схемы 1.2.0, активный контракт 1.0.0. |
| `docs/04-reference/providers/chembl/molecule.md` | Версия схемы 1.2.0, активный контракт 1.0.0. |
| `docs/04-reference/providers/chembl/protein-class.md` | Версия схемы 1.2.0, активный контракт 1.0.0. |
| `docs/04-reference/providers/chembl/publication-similarity.md` | Схема 1.2.0 и Gold v1.0, опубликован v2.0. |
| `docs/04-reference/providers/chembl/publication-term.md` | Версия схемы 1.2.0 не совпадает с активным контрактом. |
| `docs/04-reference/providers/chembl/target-component.md` | Версия схемы 1.2.0, активный контракт 1.0.0. |
| `docs/04-reference/providers/crossref/publication.md` | Версия схемы 1.2.0, активный контракт 1.0.0. |
| `docs/04-reference/providers/openalex/publication.md` | Версия схемы 1.2.0, активный контракт 1.0.0. |
| `docs/04-reference/publication-fields-reference.md` | Утверждение, что _run_id не пишется в Silver, не совпадает с publication.yaml. |
| `docs/04-reference/publication-validation-index.md` | Номера ADR перепутаны с текущим реестром. |
| `docs/04-reference/templates/pipeline-review-checklist.md` | Флаг forensic-retention снят со sink-схемы. |
| `docs/04-reference/workflow-catalog.md` | Ссылка на services/workflow_runner_service.py, файл лежит в services/workflow/. |
| `docs/05-operations/archive-index.md` | release-checklist.md назван историческим v5.9, файл сейчас активный шаблон v6.x. |
| `docs/05-operations/deployment/neo4j-audit-instance-guide.md` | Запуск идёт через отсутствующий scripts/ops/start-neo4j-audit.ps1. |
| `docs/05-operations/deployment/neo4j-audit-instance-implementation.md` | Тот же отсутствующий start-neo4j-audit.ps1 и NEO4J_AUDIT_INSTANCE_GUIDE.md. |
| `docs/05-operations/deployment/neo4j-audit-instance-quick-start.md` | Вызов scripts/ops/start-neo4j-audit.ps1 и src.tools.neo4j_audit не совпадает с деревом. |
| `docs/05-operations/deployment/neo4j-memory-setup.md` | Цитируется отсутствующий docs/99-archive/operations/neo4j-root-status-2026-04/. |
| `docs/05-operations/release-checklist.md` | Чеклист утверждает hard_fail 25%, в configs/base/quality.yaml стоит 0.50. |
| `docs/05-operations/runbooks/incident-response.md` | Метрика errors-total{type=recoverable} не совпадает с bioetl_errors_total. |
| `docs/05-operations/runbooks/merge-campaign.md` | Обязательный pytest tests/snapshots не собирает тесты: нет test_*.py. |
| `docs/05-operations/runbooks/observability-checklist.md` | Регрессия указывает на отсутствующий test_checkpoint_compatibility_service.py. |
| `docs/05-operations/runbooks/scaling.md` | Процедура требует SQL OPTIMIZE/ZORDER, такой поверхности в CLI нет. |
| `docs/05-operations/sli-slo-baseline.md` | Алерт BioETLQuarantineExplorerUnavailable отсутствует в prometheus rules. |
| `docs/05-operations/vacuum-retention.md` | Пути medallion_lifecycle.py и vacuum_service.py в указанных местах отсутствуют. |
