# ID Generation Rules

*Статус: internal-published (Internal / Extended)*

## Format
Use stable, semantic IDs with lowercase kebab-case:

`EV-<pillar>-<topic>-<descriptor>`

Examples:
- `EV-market-pricing-smb-wtp`
- `EV-tech-latency-inference-baseline`

## Rules
- Do not include dates in IDs.
- Keep IDs immutable after creation.
- Reuse existing IDs when updating the same evidence object.
