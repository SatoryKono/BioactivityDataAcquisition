______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# Архитектурные документы (канонические ссылки)

Этот индекс фиксирует канонические ссылки на архитектурные документы, которые
часто упоминаются в аудиторских шаблонах.

Для published contracts, CLI surfaces, provider/pipeline specs и API reference
используйте [Reference Index](../04-reference/index.md); этот индекс покрывает
именно architecture-side entry points.

| Запрошенный документ  | Канонический документ                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Domain Objects        | [01-domain-layer.md](../02-architecture/01-domain-layer.md)                                                         |
| ETL Layers            | [data-layers.md](../02-architecture/data-layers.md)                                                                 |
| Data Flow             | [data-flow.md](../02-architecture/diagrams/guide/data-flow-reference.md)                                            |
| Duplication Reduction | [module-consolidation-migration-requirements.md](../02-architecture/module-consolidation-migration-requirements.md) |
| Physical Layout       | [03-file-policy.md](governance/03-file-policy.md) + [local-storage-layout.md](../03-guides/local-storage-layout.md) |
| DQ Contract System    | [ADR-045-dq-contract-system.md](../02-architecture/decisions/ADR-045-dq-contract-system.md)                         |

> **Примечание:** Ранее использовались файлы-алиасы (`01-domain-objects.md`,
> `02-etl-layers.md` и т.д.) в `docs/00-project/`. Они удалены — используйте
> канонические документы напрямую.

## Workflow Control Plane (ADR-047)

- Target model: immutable `WorkflowManifest`, append-only `WorkflowLedger`, and mutable `WorkflowExecutionState`.
- Local runtime safety: one `MemoryLock` per workflow name (ADR-010 local-only boundary).
- Operator command flow: `bioetl workflow run`, `--resume-last`, `--repair-steps`, `--force-steps`, `bioetl workflow status`.

Canonical sources:

- [ADR-047](../02-architecture/decisions/ADR-047-workflow-control-plane.md)
- [Workflow Object](../03-guides/workflows.md)
- [Workflow Control-Plane Recovery](../05-operations/runbooks/workflow-control-plane.md)
- [POST_CHANGE_VALIDATION](ai/agents/policy/POST_CHANGE_VALIDATION.md)

Deprecated framing (do not use):

- resume logic as ledger-only mutable state;
- resume keyed only by workflow name without execution fingerprint.
