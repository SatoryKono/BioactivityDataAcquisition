______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Data Quality Investigation Procedures

**Issue:** #6549
**SSOT:** [dq-configuration.md](../03-guides/dq-configuration.md),
[dq-contracts](../04-reference/contracts/dq-contracts.md),
[pipeline-failure-dq](runbooks/pipeline-failure-dq.md),
[cheatsheets/data-quality-rules](../03-guides/cheatsheets/data-quality-rules.md)

## Workflow

1. **Detect** — hard/soft threshold, quarantine spike, or CI contract failure.
2. **Scope** — pipeline, run_id, batch_id, layer (Silver vs Gold).
3. **Classify** — completeness / validity / consistency / uniqueness / schema.
4. **Sample** — quarantine rows + matching Bronze raw.
5. **Root cause** — source vs profile vs schema vs threshold misuse.
6. **Remediate** — code/config/data fix; re-run or quarantine replay.
7. **Evidence** — keep failed run artifacts; do not rewrite history.

## Multi-default thresholds (do not misread)

| Surface | hard_fail default |
| --- | ---: |
| Hierarchical `quality:` / `configs/base/quality.yaml` | **0.50** |
| Contract loader omitted thresholds | **0.50** |
| Silver request / pipeline-override baseline | **0.20** |

## Tools

- `bioetl quarantine inspect …`
- DQ report sidecars for the run
- Pandera models in domain schemas/contracts
- Enum/vocab registries under `configs/enums/**`, `configs/vocab/**`

## Common issues

| Issue | First check |
| --- | --- |
| Null handling | profile null canonicalization |
| Enum/regex fail | SSOT enum YAML vs observed inventory |
| Range violations | unit normalization (ChEMBL activity) |
| Uniqueness | identity keys / content_hash |
| Sudden rate jump | upstream feed change or deploy regression |

## Threshold changes

Raising `hard_fail` requires the **mandatory evidence gate** in dq-contracts
(before/after impact, owner approval, rollback condition). Green-washing is
forbidden.

## Related

- [quarantine tutorial](../03-guides/tutorials/quarantine-system.md)
- Sequence: `diagrams/sequence/04-dq-validation-sequence.mmd`
