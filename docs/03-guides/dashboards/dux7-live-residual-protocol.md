# DUX7 live residual protocol (a11y / contrast / theme / copy / screenshots)

**Status:** active  
**Wave:** DUX7  
**Predecessor residual:** DUX6 live-only items in `dux6-residual-readability.md`

## Scope

1. WCAG 2.2 AA contrast on real Grafana theme tokens (dark required; light measured or unsupported)
2. Keyboard/focus walkthrough for nav bus (`aria-current`, tab order, focus visible)
3. Light theme parity **or** explicit unsupported decision with evidence
4. Native Copy/Open for Run/Manifest identity values (data links on ID tables)
5. Live screenshot matrix SG-01..SG-07 at 1366×768, 1440×900, 1920×1080 (100%; 125% when feasible)

## Tooling

```bash
# auth from runtime env (GRAFANA_PASSWORD / token)
python -m scripts.ops check-grafana-audit-preflight --json --skip-screenshot-check

# copy affordance apply
python scripts/ops/observability/grafana/apply_dux7_live_residual.py

# live residual runner (contrast + a11y + screenshots)
python scripts/ops/observability/grafana/run_dux7_live_residual.py --output-dir reports/quality/dux7-live-evidence
```

## Acceptance

- Evidence JSON/markdown under `reports/quality/dux7-live-evidence/`
- Dark theme contrast report for nav chips + status colors
- Keyboard/nav focus notes with pass/fail
- Light theme: measured OR documented unsupported
- ID panels expose `data:text/plain` Copy/Open link
- Screenshot matrix covers 7 UIDs × target viewports (or explicit blocker)

## Constraints

- No invent metrics; no Prom `run_id` labels
- Do not edit `.env` files without explicit approval
- Grafana remains interface adapter for verdict semantics
