Parent: #7167

Task ID: `GRA-RT-03`
Priority: `P2`

## Problem

The canonical renderer does not expose a kiosk capture profile, so responsive
behavior at 2560×1440 and 3840×2160 is `UNKNOWN`. Layout consistency was
confirmed by manual review of two 1440×900 Dark groups, but no deterministic
geometry comparison currently guards against random layout shifts.

## Evidence

- `reports/observability/grafana/render-audit-20260729/AUDIT.md`
- render groups `1440x900-dark` and `1440x900-dark-repeat`

Evidence source: `RUNTIME_RENDER`

Confidence: `FACT`

## Scope

1. Add canonical kiosk profiles at 2560×1440 and 3840×2160 in Dark and Light.
2. Persist the applied kiosk query/state and 100% zoom in each manifest.
3. Add a repeat-render consistency check based on stable geometry and
   typography signals.
4. Mask or exclude live values, relative timestamps, refresh indicators, and
   other intentionally dynamic regions.
5. Report dashboard UID and panel ID for any detected shift.

## Acceptance criteria

- [ ] Kiosk mode is confirmed from browser state, not inferred from requested
      URL parameters.
- [ ] All seven UIDs render at 2560×1440 and 3840×2160 in both themes.
- [ ] Checks cover clipping, wrapping, overflow, panel resize, navigation,
      selectors, legends, tables, and responsive typography.
- [ ] Repeat renders compare panel bounding boxes, row heights, navigation
      wrapping, scrollbar presence, and typography.
- [ ] Live-data changes do not create false layout failures.
- [ ] Failures identify the dashboard UID and affected panel.
- [ ] Pixel hash is not the sole consistency criterion.

## Validation

```bash
.venv/bin/python -m scripts.ops rerender-grafana
.venv/bin/python -m pytest -q tests/integration/test_grafana_render_*.py
```

## Out of scope

- adopting an external kiosk service;
- making Grafana mandatory;
- causal usability claims from screenshots alone.

