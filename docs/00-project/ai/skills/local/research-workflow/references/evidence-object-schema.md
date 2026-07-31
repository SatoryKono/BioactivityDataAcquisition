# Evidence Object Schema

Use this schema when writing `02-evidence/<pillar>/EV-*.yaml`.

## Required Fields

| Field                 | Type         | Description                                                                         |
| --------------------- | ------------ | ----------------------------------------------------------------------------------- |
| `id`                  | string       | Semantic evidence ID such as `EV-market-pricing-smb-wtp`                            |
| `pillar`              | string       | Research pillar, for example `market` or `users`                                    |
| `source.type`         | string       | Source class: `url`, `pdf`, `interview`, `internal-doc`, `experiment`, or `dataset` |
| `source.ref`          | string       | URL, document name, dataset handle, or other traceable reference                    |
| `source.retrieved_at` | date         | Retrieval date in `YYYY-MM-DD` format                                               |
| `claim`               | string       | Specific, falsifiable statement supported by the source                             |
| `confidence`          | float        | Confidence score in the range `0.0-1.0`                                             |
| `assumptions`         | list[string] | Explicit assumptions required to accept the claim                                   |

## Optional Fields

| Field   | Type         | Description                             |
| ------- | ------------ | --------------------------------------- |
| `quote` | string       | Supporting quote, statistic, or excerpt |
| `notes` | string       | Context, caveats, or limitations        |
| `tags`  | list[string] | Searchable topical tags                 |

## Canonical Example

```yaml
id: EV-market-pricing-smb-wtp
pillar: market
source:
  type: url
  ref: "https://example.com/pricing-research"
  retrieved_at: 2026-01-21
claim: "SMB segment willingness-to-pay peaks at $29/mo for productivity tools."
quote: "Our survey of 500 SMBs found median WTP of $29/month..."
confidence: 0.75
assumptions:
  - "Survey sample is representative of the target segment"
  - "The product category is close enough to our use case"
notes: "Sample skewed toward US companies. Regional validation still needed."
tags:
  - pricing
  - smb
  - wtp
```

## Validation Checklist

- `claim` is concrete enough to be disproven.
- `confidence` is present and realistically calibrated.
- At least one assumption is listed.
- `source.ref` is traceable enough to revisit later.
- `id` follows the semantic ID rules.
