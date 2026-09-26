> Archived snapshot. The maintained guide remains at
> [DUX6 residual readability](../../../03-guides/dashboards/dux6-residual-readability.md).

# DUX6 residual readability (post-DUX5 re-audit)

**Status:** archived  
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

The completed DUX5/DUX6 one-shot applicators were retired on 2026-08-19.
The shipped dashboard JSON and archived evidence are the durable record;
`render_nav_bus.py` remains the maintained navigation generator.

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

**CLOSED by DUX7** — see
[dux7-live-residual-protocol.md](dux7-live-residual-protocol.md) and
`reports/quality/dux7-2026-07-29-closeout.md`.

- ~~WCAG contrast~~ → DUX7 PASS
- ~~Keyboard/focus a11y~~ → DUX7 PASS
- ~~Light theme~~ → DUX7 `supported_theme_safe_nav`
- ~~Copy affordance~~ → DUX7 data:text/plain on ID panels
- ~~Screenshot matrix~~ → DUX7 42/42 evidence

## DUX7 live residual

Live residual closeout protocol: [dux7-live-residual-protocol.md](dux7-live-residual-protocol.md).
