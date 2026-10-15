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

> **Resolution wave 2026-10-15:** 69 entries were fixed against the current tree
> and removed from the table below (canonical renames ChemblAdapter /
> PipelineService / *Service suffixes, storage port family names,
> StoragePort -> Bronze/Silver/Gold/Merged ports in description cards,
> provider schema versions 1.2.0 -> contract versions, entity/BPK spec names,
> ADR path updates). Fixed files were stamped `2026-10-15`.


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
| `docs/02-architecture/decisions/ADR-017-observability-architecture.md` | Путь composition/observability_api.py устарел. |
| `docs/02-architecture/decisions/ADR-019-observability-port-enforcement.md` | Реализация привязана к отсутствующим interfaces/orchestration/signals.py. |
| `docs/02-architecture/decisions/ADR-021-ddd-aggregates-adoption.md` | Указан отсутствующий _quarantine_entry_transitions_mixin.py. |
| `docs/02-architecture/decisions/ADR-022-tracing-noop.md` | NoOpTracing импортируется не из того модуля. |
| `docs/02-architecture/decisions/ADR-023-entity-type-patterns.md` | Ссылка на отсутствующий docs/audits/entity_type-audit.md. |
| `docs/02-architecture/decisions/ADR-024-entity-naming-unification.md` | Пути docs/glossary.md и configs/naming-exceptions.yaml отсутствуют. |
| `docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md` | Ссылка на отсутствующий src/bioetl/domain/config.py. |
| `docs/02-architecture/decisions/ADR-028-filter-rules-externalization.md` | Точка интеграции config_loader.py отсутствует. |
| `docs/02-architecture/decisions/ADR-029-output-metadata-unification.md` | Указанные metadata_coordinator.py и metadata_builder.py отсутствуют. |
| `docs/02-architecture/decisions/ADR-030-publication-pagination-strategy.md` | Implementation указывает отсутствующие фабрики и domain/config.py. |
| `docs/02-architecture/decisions/ADR-031-loading-strategy-formalization.md` | Implementation указывает отсутствующие services_factory.py и pipeline_factory.py. |
| `docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md` | Иерархия configs/validation/pubmed/publication.yaml отсутствует. |
| `docs/02-architecture/decisions/ADR-037-canonical-schema-generation.md` | Экспортер указан в src/tools, файл лежит в scripts/schema/generation/. |
| `docs/02-architecture/decisions/ADR-039-unified-entity-config-format.md` | config_loader.py как orchestration-модуль отсутствует. |
| `docs/02-architecture/diagrams/descriptions/architecture/03-medallion-data-flow.md` | Узлы CircuitBreaker/RateLimiter/TokenBucket не совпадают с классами Guard/RateLimiter. |
| `docs/02-architecture/diagrams/descriptions/architecture/10-resilience-patterns.md` | Узел CircuitBreaker не совпадает с CircuitBreakerGuard. |
| `docs/02-architecture/diagrams/descriptions/architecture/15-batch-executor-internals.md` | Названы отсутствующие PipelineProcessingPort и BatchStateCommitPort. |
| `docs/02-architecture/diagrams/descriptions/architecture/16b-transformer-pub-other.md` | Имена трансформеров не совпадают с *PublicationTransformer. |
| `docs/02-architecture/diagrams/descriptions/architecture/21-idempotent-processing-guards.md` | CheckpointLoadService и CompositeRunner не совпадают с текущими классами. |
| `docs/02-architecture/diagrams/descriptions/foundation/24-hash-service-class.md` | Класса ContentHashService в src нет. |
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
| `docs/02-architecture/diagrams/governance/diagram-views-inventory.md` | Счётчик .mermaid и список семейств не совпадают с деревом. |
| `docs/02-architecture/diagrams/governance/diagram-views-plan.md` | Родительские пути названы .mermaid, канон лежит как .mmd. |
| `docs/02-architecture/history/compatibility-facade-review-history.md` | publication_field_groups.py всё ещё помечен retained, модуля нет. |
| `docs/02-architecture/module-consolidation-migration-requirements.md` | Стартовый путь domain/value-objects неверен, пакет называется value_objects. |
| `docs/04-reference/api/application.md` | Package exports сервисов сняты, перечисленные классы отсутствуют. |
| `docs/04-reference/api/application/services.md` | services/__init__.py оставил пустой __all__. |
| `docs/04-reference/api/composition.md` | Названы отсутствующие runtime-модули и классы CrossrefAdapterFactory/PipelineContractValidator. |
| `docs/04-reference/api/index.md` | Бюджет cross_layer_group_edges_total 334 не совпадает с 330 в коде. |
| `docs/04-reference/components/config-runtime-artifacts.md` | get_config_drift и ConfigDriftReport в src отсутствуют. |
| `docs/04-reference/contracts/canonical-field-registry.md` | Артефакты аудита 2026-05-15 указаны как текущие, их нет в reports/. |
| `docs/04-reference/domain/control-plane.md` | Названы отсутствующие RunManifestArtifact и классы RunLedger/WorkflowLedger. |
| `docs/04-reference/domain/ports.md` | Каталог утверждает 74 файла, в domain/ports их 81. |
| `docs/04-reference/domain/symbol-invariant-traceability.md` | События BatchCompleted и QuarantineResolved отсутствуют. |
| `docs/04-reference/domain/value-objects.md` | Каталог неполон: нет orcid.py и export_identity.py. |
| `docs/04-reference/hash-policy.md` | Путь tests/unit/domain/hash-policy/ неверен, ключи YAML другие. |
| `docs/04-reference/pipelines/chembl/08-assay-parameters-spec.md` | Текущим Gold назван v1.0, registry держит 2.0.0. |
| `docs/04-reference/pipelines/chembl/12-publication-similarity-spec.md` | Текущим экспортом назван v1.0, опубликован только 2.0.0. |
| `docs/04-reference/pipelines/contract-facet-matrix.md` | Счётчики required/nullable не совпадают с contract-coverage-matrix.json. |
| `docs/04-reference/publication-fields-reference.md` | Утверждение, что _run_id не пишется в Silver, не совпадает с publication.yaml. |
| `docs/04-reference/publication-validation-index.md` | Номера ADR перепутаны с текущим реестром. |
| `docs/04-reference/templates/pipeline-review-checklist.md` | Флаг forensic-retention снят со sink-схемы. |
| `docs/04-reference/workflow-catalog.md` | Ссылка на services/workflow_runner_service.py, файл лежит в services/workflow/. |
