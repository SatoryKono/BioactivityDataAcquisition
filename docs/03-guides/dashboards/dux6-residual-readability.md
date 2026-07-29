# DUX6 residual readability (post-DUX5 re-audit)

**Status:** active  
**Epic:** #7139  
**Predecessor:** DUX5 #7116 (closed)

## Intent

DUX5 closed contract/copy residual. DUX6 enforces **pixel/operator residual** from the
re-submitted screenshot audit (SG-01..SG-07):

- UNKNOWN always paired with reason class (description + Provenance)
- triage text fits without internal scroll
- Value columns labelled; paths hidden on browse/artifacts
- evidence stats prefer value color over full-surface green/red
- empty charts distinguish none-observed vs missing telemetry
- integer percent precision; zero applicability grammar

## Applicators

1. `scripts/ops/observability/grafana/apply_dux5_residual.py`
1. `scripts/ops/observability/grafana/_fix_no_scroll_triage_panels.py`
1. `scripts/ops/observability/grafana/apply_dux6_residual.py`
1. `scripts/ops/observability/grafana/render_nav_bus.py`

## Copy SSOT

- [dux5-copy-dictionary.md](dux5-copy-dictionary.md)
- [dux5-screenshot-regression-protocol.md](dux5-screenshot-regression-protocol.md)
- [verdict-ontology.md](verdict-ontology.md)

## Title policy

Panel titles with `Monitor:` / `Track:` / `Inspect:` remain contract-stable (DUX4-01 Approach B).

## L0 tokens

Status enum tokens stay `OK/WARN/CRIT/UNKNOWN/INCOMPLETE` for metric-semantics tests.
Operator expansion lives in Provenance + descriptions.

## Residual still live-only

- WCAG contrast computation on real theme tokens
- Keyboard/focus a11y walkthrough
- Light theme parity (or explicit unsupported)
- True Copy button UX if Grafana panel plugin cannot provide it (use data links / explorer)

## DUX7 live residual

Live residual closeout protocol: [dux7-live-residual-protocol.md](dux7-live-residual-protocol.md).
