# Evidence Object Schema

## Required Fields
- `id`
- `pillar`
- `source.type`
- `source.ref`
- `source.retrieved_at`
- `claim`
- `confidence`

## Optional Fields
- `quote`
- `assumptions`
- `notes`
- `tags`

## Minimal Example
```yaml
id: EV-market-pricing-smb-wtp
pillar: market
source:
  type: url
  ref: https://example.org/report
  retrieved_at: 2026-03-03
claim: SMB median WTP is near $29 per month.
confidence: 0.75
```
