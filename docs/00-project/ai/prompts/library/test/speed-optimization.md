---
id: prompt.tests.speed-optimization
version: 2.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- SCOPE
- TARGET_SPEEDUP_PCT
- BASELINE_RUNS
- LANGUAGE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
related_ssot:
- AGENTS.md
- docs/00-project/RULES.md
- pyproject.toml
- scripts/engineering/dev/run_pytest.sh
anti_patterns:
- Disabling tests for speed
- Comparing incomparable suites (benchmark/slow mixed in)
- Claims without before/after numbers
tags:
- tests
- performance
- operator
summary: Accelerate test runs without weakening coverage
---
# Test speed optimization loop

Accelerate BioETL test runs by at least `TARGET_SPEEDUP_PCT` without reducing
check reliability.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | test surface / suite focus (e.g. `tests/unit`) |
| `TARGET_SPEEDUP_PCT` | `30` |
| `BASELINE_RUNS` | `3` (median wall-clock) |
| `LANGUAGE` | `ru` |

## Context

- Prefer project wrappers: WSL `bash scripts/engineering/dev/run_pytest.sh`,
  Windows `.\scripts\engineering\dev\run_pytest.ps1`; CI/single-OS may use
  `uv run python -m pytest`.
- Markers: `unit`, `integration`, `e2e`, `architecture`, `benchmark`, `serial`,
  `slow`. Benchmarks and `slow` are excluded by default — do not compare
  incomparable sets.
- Respect architecture rules; do not weaken test truthfulness for speed.

## Steps

1. **Study** test contour: `pyproject.toml`, `tests/`, conftest files, pytest
   wrappers, relevant CI workflows.
2. **Find** real bottlenecks: collection time, heavy fixtures, import side
   effects, serial tests, xdist/cache/import-mode, VCR-heavy paths, sleep/I/O.
3. **Baseline**: 1–2 developer-realistic scenarios; ≥`BASELINE_RUNS` runs each;
   record command, count, pass/fail, environment; use median wall-clock.
4. **Plan**: highest-effect, cheapest reversible changes; hypothesis, expected
   gain, risk, verification.
5. **Implement** in small steps; re-run relevant checks after each meaningful change.
6. **Re-measure** same scenarios/method; compute % speedup vs baseline.
7. If below target: new hypotheses only; record what already failed.
8. **Stop** at ≥ target speedup **or** only high-risk/low-confidence leftovers
   with an honest residual report.

## Hard limits

- Do not disable tests to “speed up” if that changes coverage meaning
- Do not lower check strictness without explicit justification
- Do not break CI parity without strong reason
- Performance claims need numbers before/after

## Result format

- baseline · bottlenecks · plan · changes · measurements · % speedup · residual risks
