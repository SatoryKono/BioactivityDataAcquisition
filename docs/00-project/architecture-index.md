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
