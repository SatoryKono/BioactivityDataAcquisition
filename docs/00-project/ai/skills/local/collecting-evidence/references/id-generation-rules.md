# Evidence ID Generation Rules

Evidence objects must use semantic IDs so the content is understandable without opening the file.

## Canonical Pattern

```text
EV-<pillar>-<topic>-<qualifier>
```

Examples:

- `EV-market-pricing-smb-wtp`
- `EV-users-onboarding-dropoff`
- `EV-tech-api-rate-limit`

## Rules

1. Always start with the `EV-` prefix.
2. Use the pillar name as the first segment after the prefix.
3. Use lowercase kebab-case only.
4. Prefer topic words that describe the underlying claim, not the source.
5. Add a short qualifier only when it disambiguates similar evidence.
6. Keep the ID stable once the evidence object is referenced elsewhere.

## Good IDs

- `EV-market-growth-remote-tools`
- `EV-competitors-pricing-benchmark`
- `EV-economics-smb-unit-economics`

## Bad IDs

- `EV-001`
- `EV-market-study`
- `EV-random-note-final`

## Pillar Names

Use one of the standard ledger pillars:

- `market`
- `users`
- `tech`
- `competitors`
- `design`
- `legal`
- `ops`
- `economics`

