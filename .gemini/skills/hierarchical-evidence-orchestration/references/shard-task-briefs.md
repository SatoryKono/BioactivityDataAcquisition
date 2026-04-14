# Shard Task Briefs

Use these briefs when launching child shard work.

## Collector Brief

```text
Use $collecting-evidence.

Topic: <shard-topic>
Scope: <scope>
Output root: docs/reports/evidence/<shard-topic>/

Deliverables:
- 01-pillars/PILLARS.md
- 02-evidence/<shard-topic>/RAW-<shard-topic>-<date>.md
- minimum 5 EV-*.yaml
- SUMMARY.md

Constraints:
- evidence-first only
- no synthesis
- no decisions
- write only inside the shard output root

Return:
- evidence count
- top claims
- gate status
```

## Synthesizer Brief

```text
Use $synthesizing-pillars.

Topic: <shard-topic>
Input root: docs/reports/evidence/<shard-topic>/

Deliverables:
- 03-synthesis/SYN-<shard-topic>.md

Constraints:
- cite EV-* ids
- record contradictions explicitly
- do not create decisions
- write only inside the shard output root

Return:
- evidence analyzed
- key insights count
- contradictions count
- synthesis status
```

## Parent Cross-Synthesis Reminder

Parent cross-synthesis is not a shard synthesis replay.

It should answer:

- what patterns repeat across shards
- what tensions cross shard boundaries
- which themes are broad but not yet actionable
- which themes are confirmed enough to justify later decision work
