---
description: "Иерархический каскадный аудит документации BioETL. Режимы: full, layers, providers, architecture, governance, crossref."
---

# /documentation-cascade-audit

Hierarchical multi-agent documentation audit with auto-scaling.

## Использование
```
/documentation-cascade-audit [mode] [scope]
```

**Режимы:** `full` (default), `layers`, `providers`, `architecture`, `governance`, `crossref`

## Инструкции

Load the full specification from `.claude/skills/documentation-cascade-audit.skill.md` and execute as L1 orchestrator.

This skill is too large to inline (1168 lines). It defines:
- L1 orchestrator → L2 layer/provider auditors → L3 module specialists
- 5 documentation types: docstrings, API ref, guides, contracts, architecture
- Auto-scaling based on workload score
- Aggregation and final report

Launch via Agent tool with `subagent_type="py-doc-swarm"`.

Arguments: $ARGUMENTS
