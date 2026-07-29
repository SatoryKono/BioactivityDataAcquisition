# DUX5 screenshot & accessibility regression protocol

**Issue:** #7133 (DUX5-31)  
**Parent epic:** #7116

## Purpose

Prevent readability defects (clipping, internal scroll, bare UNKNOWN, false-red zeros)
from re-entering `grafana/dashboards/*.json` without merge-blocking evidence.

## Baseline viewports

| Viewport | Zoom | Theme |
| --- | ---: | --- |
| 1366×768 | 100%, 125% | dark (required) |
| 1440×900 | 100% | dark |
| 1920×1080 | 100% | dark |
| light | 100% | document unsupported if not verified |

## Assertions (non-pixel)

1. No internal vertical scrollbar on first-screen Status / Provenance / First Action / Next actions
2. Status, Reason, Impact, Action visible without tooltip-only disclosure
3. No bare `VALID_EMPTY` / raw `GET /ops` in panel bodies
4. No `Value #*` column headers without displayName
5. Nav bus `id=1000` shows chips `0. Trust` … `6. Run Explorer` without truncation marker
6. Typography floors from `dux5-copy-dictionary.md` (manual or render measure)
7. Focus/active nav distinguishable without color alone (keyboard pass)

## Capture commands

Prefer repo tools:

```bash
python scripts/ops/observability/grafana/check_grafana_dashboard_audit_preflight.py
# optional live render when stack is up:
# python scripts/ops/observability/grafana/rerender_grafana_screenshots.py
```

Store before/after under operator-local evidence; do not commit secrets.

## Exit

- [ ] Dark theme verified at 1366 baseline
- [ ] Light theme verified **or** explicitly unsupported in this file
- [ ] Linked from DUX5 pack closeout
