______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-08'

______________________________________________________________________

# Neo4j Project Memory Seed Pack

Назначение: этот файл задаёт поэтапную загрузку project memory в
`@neo4j-memory` без попытки "залить в память весь репозиторий".

Подход:

- сохранять только устойчивые факты;
- опираться на canonical docs, а не на временные выводы сессии;
- сначала загружать архитектурный каркас, потом runtime seams, потом provider
  knowledge и operational memory;
- не дублировать временные логи, инциденты и одноразовые состояния.

## Источники истины

- `docs/00-project/ai/memory/agent-memory.md`
- `docs/00-project/RULES.md`
- `AGENTS.md`
- `docs/02-architecture/00-overview.md`
- `docs/02-architecture/02-application-layer.md`
- `docs/02-architecture/05-composition-layer.md`
- `docs/reports/evidence/project-package-topology/03-synthesis/SYN-project-package-topology.md`
- `docs/reports/knowledge-graphs/bioetl-architecture-graph.json`
- `docs/reports/knowledge-graphs/bioetl-runtime-detail-graph.json`
- `src/bioetl/domain/README.md`
- `src/bioetl/domain/__init__.py`
- `configs/providers/*.yaml`
- `configs/entities/*/*.yaml`

## Phase 1: Project + Architecture

Цель: закрепить самые устойчивые знания о проекте.

Prompt 1:

```text
@neo4j-memory создай базовую память проекта BioETL и сохрани факты:
- BioETL is a Python ETL framework for bioactivity data acquisition.
- BioETL uses Hexagonal Architecture with Ports and Adapters.
- BioETL uses Medallion Architecture with Bronze, Silver, and Gold layers.
- BioETL follows a Local-Only runtime policy.
- BioETL has five runtime layers: domain, application, infrastructure, composition, interfaces.

Свяжи эти факты с проектом BioETL и покажи краткое summary сохранённого.
```

Prompt 2:

```text
@neo4j-memory сохрани архитектурные инварианты проекта BioETL:
- domain must not perform I/O
- application must not import infrastructure
- composition is the composition root
- interfaces are boundary entrypoints
- infrastructure may implement domain ports

Создай связи между слоями и инвариантами, затем покажи, что было сохранено.
```

Prompt 3:

```text
@neo4j-memory сохрани технологические опоры BioETL:
- Silver layer must use Delta Lake
- Pandera is used for dataframe validation
- content flows from Bronze to Silver to Gold
- package topology should be interpreted with governance signals, not package count alone

Свяжи эти факты с BioETL, Medallion Architecture, and governance signals.
```

## Phase 2: Runtime + Bootstrap

Цель: закрепить execution seams, которые чаще всего нужны при reasoning.

Prompt 4:

```text
@neo4j-memory сохрани execution memory для BioETL:
- PipelineRunner orchestrates pipeline lifecycle
- PreflightService validates infrastructure and medallion policy before execution
- PostrunService handles DQ, reports, compaction, and vacuum
- PipelineService is the injected service bundle for runtime execution

Свяжи эти компоненты как execution lifecycle around PipelineRunner.
```

Prompt 5:

```text
@neo4j-memory сохрани runtime bootstrap facts:
- composition/bootstrap/runtime/pipeline.py is the main runtime bootstrap entrypoint
- runtime_builders prepares runner inputs, observability, and control-plane attachments
- composition/bootstrap/runtime/composite.py bootstraps composite execution
- runner_assembly builds composite runner dependency bundles

Свяжи bootstrap entrypoints с PipelineRunner и CompositePipelineRunnerService.
```

Prompt 6:

```text
@neo4j-memory сохрани observability and control-plane facts for BioETL:
- bootstrap_observability_bundle creates logger, metrics, tracer, and DQ monitor bundle
- control-plane collaborators attach manifest and run-ledger context to runtime execution
- manifest_id can be propagated into runtime context for execution traceability

Покажи связи между observability bootstrap, control-plane, and runtime execution.
```

## Phase 3: Providers + Config Surface

Цель: зафиксировать provider landscape и config seams.

Prompt 7:

```text
@neo4j-memory сохрани provider inventory проекта BioETL:
- ChEMBL
- PubChem
- UniProt
- PubMed
- CrossRef
- OpenAlex
- Semantic Scholar

Свяжи их с проектом BioETL как Provider nodes.
```

Prompt 8:

```text
@neo4j-memory сохрани facts about config surface in BioETL:
- provider entity configs live under configs/entities/{provider}/{entity}.yaml
- composite configs live under configs/composites/{entity}.yaml
- infrastructure.config is the canonical owner for YAML loading and normalization
- composition keeps thin public config access seams for runtime entrypoints

Свяжи config facts с project, infrastructure layer, and composition layer.
```

Prompt 9:

```text
@neo4j-memory сохрани provider/runtime relationship facts:
- ProviderRegistry keeps deterministic provider and pipeline registration state
- ensure_providers_loaded is the canonical provider loading boundary
- register_all_pipelines is used during runtime bootstrap

Свяжи эти факты с runtime bootstrap and provider inventory.
```

## Phase 4: Operational Memory

Цель: сохранить только устойчивые operational facts, важные для повторного использования.

Prompt 10:

```text
@neo4j-memory сохрани operational facts for Neo4j memory in BioETL:
- neo4j-memory MCP is registered in Codex through the project wrapper
- the wrapper runs @knowall-ai/mcp-neo4j-agent-memory@0.2.5
- in WSL, Neo4j is accessed via bolt://host.docker.internal:7687
- Docker container name is bioetl-neo4j

Свяжи эти факты с BioETL and WSL runtime usage.
```

Prompt 11:

```text
@neo4j-memory сохрани env-loading facts:
- .env provides base local overrides
- .env.local provides machine-specific overrides
- shell-provided env vars override repo env files
- Neo4j connection settings can be loaded from .env or .env.local

Свяжи эти факты с the Neo4j memory operational setup.
```

Prompt 12:

```text
@neo4j-memory сохрани practical usage facts:
- docs/00-project/ai/memory/agent-memory.md is the human project memory entry point
- docs/reports/knowledge-graphs/bioetl-architecture-graph.json captures architecture-level graph context
- docs/reports/knowledge-graphs/bioetl-runtime-detail-graph.json captures runtime/bootstrap detail

Свяжи их с BioETL as memory source artifacts.
```

## Phase 5: Domain Model + Provider Semantics

Цель: закрепить устойчивый semantic vocabulary проекта и правила provider
identity/fallback/pagination.

Prompt 13:

```text
@neo4j-memory сохрани domain model facts for BioETL:
- domain contains the semantic model and must remain pure with no concrete I/O
- main domain families are ports, value_objects, entities, aggregates, services, schemas, validation, mapping, config, types, exceptions, registry, filtering, transformations, control_plane, composite, and lineage
- PipelineRun is the aggregate root for pipeline execution lifecycle tracking
- RunManifest is the immutable provenance snapshot for one launched run
- RunLedgerEntry is the append-only control-plane event linked to one manifest/run pair
- QuarantineEntry is the aggregate for quarantined data and its resolution lifecycle
- PipelineConfig is the immutable pipeline configuration object
- MedallionPolicy and LoadingStrategy are domain policy objects

Свяжи эти факты с domain layer и покажи краткое summary сохранённого.
```

Prompt 14:

```text
@neo4j-memory сохрани canonical identifier vocabulary for BioETL:
- ChemblId, DOI, PubMedId, OpenAlexId, SemanticScholarId, PubChemCid, UniProtId, InChIKey, SMILES, and TaxonomyId are canonical identifier or value-object concepts
- publication is commonly indexed by DOI, PubMedId, OpenAlexId, and SemanticScholarId
- activity is centered on activity_id
- molecule and compound are centered on molecule_id plus structure identifiers like SMILES and InChIKey
- target is centered on target_id
- protein is centered on accession
- idmapping maps target_id to uniprot_accession

Создай связи между identifier concepts, business domains, and pipeline identity rules.
```

Prompt 15:

```text
@neo4j-memory сохрани provider semantics for BioETL:
- ChEMBL uses public auth, offset pagination, CHEMBL identifiers, and is the primary upstream source for activity, assay, molecule, target, and publication entities
- PubChem uses public auth, offset pagination, PubChem CID identity, and enriches compounds from SMILES-based input
- PubMed uses api_key plus email auth, offset pagination, PMID identity, and supports PMID or title fallback semantics
- CrossRef uses email auth, cursor pagination, DOI identity, and uses DOI-first fallback with title search when DOI is missing
- OpenAlex uses email auth, cursor pagination, OpenAlexId identity, and supports DOI-first fallback with unsupported filters skipped
- Semantic Scholar uses api_key auth, offset pagination, SemanticScholarId identity, and has strict rate limits with DOI-first fallback
- UniProt uses api_key auth, offset pagination, UniProt accession identity, and supports protein plus idmapping semantics for ChEMBL target enrichment

Свяжи provider auth mode, pagination strategy, primary identifier, fallback semantics, and business-domain focus.
```

## Validation Prompts

После seed wave проверь retrieval:

```text
@neo4j-memory что ты знаешь про архитектуру BioETL?
```

```text
@neo4j-memory как в BioETL собирается runtime для PipelineRunner и CompositePipelineRunnerService?
```

```text
@neo4j-memory как подключаться к Neo4j memory backend из WSL для BioETL?
```

```text
@neo4j-memory какие domain families, core aggregates, and provider semantics определены для BioETL?
```

## Правила обновления памяти

- сохраняй только long-lived facts;
- не сохраняй временные логи и транзиентные ошибки;
- при изменении архитектуры обновляй memory после merge, а не во время
  незавершённого эксперимента;
- если факт противоречит `agent-memory.md`, `RULES.md` или accepted ADR, исправляй
  источник, а не раздувай память конкурирующими версиями.
