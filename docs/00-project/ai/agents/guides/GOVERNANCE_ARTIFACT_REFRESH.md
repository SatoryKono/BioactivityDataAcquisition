# Governance Artifact Refresh Recipe

*Status: internal-published (architecture audit M4 #6513; regen hygiene #9629)*

## Purpose

After write-capable changes under `src/bioetl/**/*.py` (and related quality
configs), refresh inventories/baselines so architecture gates do not fail on
stale hashes.

**Guardrail:** tech-debt budgets must only decrease or stay constant.

## Entrypoint

```bash
# refresh the coupled artifact set in dependency order
python -m scripts.engineering.qa.refresh_governance_artifacts

# verify the same set without writes; any failed checker returns non-zero
python -m scripts.engineering.qa.refresh_governance_artifacts --check
```

Do not invoke individual generators to assemble a coupled refresh. The unified
entrypoint is the PR-checklist command and prevents a partial bundle from being
reported as current.

## Ordered artifact set

The refresh path runs these existing owners in order; it does not introduce a
new YAML registry:

1. unified source-tree manifest;
2. module coverage inventory `source_tree_sha256` (preserving measured rows
   when `coverage.xml` is absent);
3. architecture dependency map;
4. test-governance and fixture-duplication snapshots;
5. hotspot family baseline and shrink-only scorecard alignment;
6. dead-code inventory;
7. architecture quality scorecard;
8. config-surface backlog;
9. live residual snapshot;
10. debt-governance gates, always last.

`--check` verifies the corresponding check-capable artifacts plus the focused
coverage/scorecard guards. It fails immediately with the failing subprocess
exit code; a preceding drift cannot be hidden by later green checks.

## Related

- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md` post-change validation section
- Issues: #6513 (M4), #9629 (regen hygiene), umbrella #6506
