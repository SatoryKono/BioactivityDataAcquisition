# Step 02 — Diagrams audit

## Executive summary

The diagram corpus has strong source and artifact controls: 277 canonical
`.mmd`, 165 decomposed `.mermaid`, and 441 tracked SVGs are covered by lint,
quality, artifact, visual-smoke, and architecture tests. One P1 tooling defect
is PROVEN: five commands advertised by the canonical router fail before their
checks run because repository imports are not bootstrapped.

`surface_score: 1` (weak) before remediation. The underlying controls pass
with an explicit `PYTHONPATH=.` workaround, but the documented quality-gate
entrypoint is not self-contained.

## Evidence

| Surface | Result |
| --- | --- |
| Diagram policy lint | 441 passed; 0 errors; 292 warnings |
| Quality gates DIAG-T018..T023 | 6 PASS; 0 hard failures; 0 warnings |
| Required SVG artifacts | 6/6 PASS |
| Visual smoke baselines | 6/6 PASS |
| SVG text visibility | 6/6 PASS |
| Class-method render integrity | 94/94 PASS |
| Diagram architecture tests | 128 PASS |
| Unpinned `npx -y` in CI/render scripts | none found |
| Canonical router help sweep | 25 PASS; 5 FAIL |

## Finding

`DIAGRAM-SEQ-001` (P1 / High): repository-root bootstrap is missing in five
direct-script targets. Machine-readable evidence is in `findings.json`.

## Blocked evidence

Fresh Mermaid syntax render is `ENVIRONMENT`: the available host binary is
`mmdc 11.12.0`, while repository policy pins `10.6.1`. The wrapper correctly
fails closed. The pinned Docker image is not present locally, so no version
override was used. Existing rendered artifacts and smoke hashes remain green.

## Residual observations

The 292 lint warnings are non-blocking baseline signals (mostly 90-day
freshness, decomposed size, and label-density warnings); no lint error or
diagram/code contradiction was proven. Token/API-key hits are field names or
rate-limit semantics, not secret values.
