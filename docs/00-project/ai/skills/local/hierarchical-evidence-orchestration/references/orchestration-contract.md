# Orchestration Contract

Use this contract for the parent topic pack.

## Parent Files

- `docs/reports/evidence/<topic_id>/ORCHESTRATION.md`
- `docs/reports/evidence/<topic_id>/SUMMARY.md`
- `docs/reports/evidence/<topic_id>/03-synthesis/CROSS-SYNTHESIS-<topic_id>.md` when synthesis is in scope

## Required Sections For `ORCHESTRATION.md`

1. Topic
1. Mode
1. Shard strategy
1. Shard map
1. Agent ownership
1. Output roots
1. Gate rules
1. Aggregation plan

## Minimal `ORCHESTRATION.md` Shape

```md
# Orchestration: <topic_id>

- Mode: `collect | synthesize | full`
- Shard strategy: `by-layer | by-package-family | by-doc-domain | custom`
- Parent output root: `docs/reports/evidence/<topic_id>/`

## Shards

| Shard | Scope | Output Root | Status |
|---|---|---|---|
| `<shard-a>` | ... | `docs/reports/evidence/<shard-a>/` | planned |
| `<shard-b>` | ... | `docs/reports/evidence/<shard-b>/` | planned |
```

## Gate Rules

- collection gate: minimum 5 `EV-*.yaml` per shard unless scope is explicitly narrower
- synthesis gate: shard evidence gate must already pass
- parent cross-synthesis gate: at least 2 synthesized shards, or explicit note why fewer are acceptable
