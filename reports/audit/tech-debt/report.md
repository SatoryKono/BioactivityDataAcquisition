# Technical debt audit

- prompt: `prompt.audit.tech-debt` 1.3.0
- HEAD: `e1c184857e460461bbb3e20829e60ab8bb262e2f` (worktree `nine-domain-audit-9f71c6444175`)
- SCOPE: `reports/quality/`, `configs/quality/`, `src/`
- MODE: `audit` / AUDIT_MODE: `full` / REQUIRE_GH_TRACKING: `false`
- Дата проверки (UTC): 2026-09-26T08:43:27Z
- surface_score: **2** — baseline exemptions и test-governance под контролем; release debt-gates и registry digest требуют refresh.

## Итог

| сигнал | значение |
| --- | --- |
| `debt_scorecard` baseline exemptions | **0** / 0 |
| test-governance `budget_violations` | **[]** |
| composition modules | **279** / cap **295** (util **0.9458**) — shrink-тест #10595 **pass** |
| architecture integral (committed scorecard) | **10.0** / excellent |
| module coverage (inventory summary) | **2491** modules; fully **2483**; partial **7**; uncovered **0** |
| debt-governance gates (live `--check`) | **43 pass / 3 fail**; `release_gate_status=failing` |
| `validate-technical-debt-audit` | exit **1** (`evidence_surface_sha256 is stale`) |

Повышение debt/quality budgets **не** рекомендуется. На этом SHA закрыт прежний риск composition>280 (285 модулей на более раннем HEAD); повторная проверка: **279** `.py` файлов.

## Находки (11)

| id | P | status | суть |
| --- | --- | --- | --- |
| TD-001 | P1 | PROVEN | Stale quality artifacts → 3 failing debt-governance gates |
| TD-002 | P1 | PROVEN | `evidence_surface_sha256` registry не пересчитан |
| TD-003 | P2 | PROVEN | 7 partially covered modules |
| TD-004 | P2 | PROVEN | application_core fan-in **6/7** (near budget) |
| TD-005 | P2 | PROVEN | 6 oversized modules на split-on-touch inventory |
| TD-006 | P2 | PROVEN | Retirement triage 17 + zero-import residue 2 |
| TD-007 | P2 | PROVEN | Public entrypoints/facades на потолке 12/3 |
| TD-008 | P2 | PROVEN | Constructor waiver QuarantineEntry (expiry 2026-12-31) |
| TD-009 | P2 | PROVEN | Publication semantic compatibility (2 fields) |
| TD-010 | P3 | PROVEN | 83 classified assertless smoke tests |
| TD-011 | P3 | PROVEN | domain/aggregates hold-flat 8/8 (#10552) |

## TD-001 — artifact drift

`python -m scripts.engineering.qa report-debt-governance-gates --check` @ 2026-09-26, exit **1**:

- `module_coverage_source_tree_hash_current` — inventory hash не совпадает с live деревом
- `module_coverage_scorecard_coherence` — inventory **2491** vs scorecard **2494**; hash `1ad4a664…` vs `c90a8bde…`
- `generated_artifact_drift` — 4 stale: scorecard, hotspot baseline, module inventory, remote_main baseline

Remediation: канонический refresh (`report-module-coverage`, CI drift families, `--update` gates) без роста лимитов.

## TD-002 — registry digest

`validate-technical-debt-audit --json` → `ok=false`, единственный issue: stale `evidence_surface_sha256`. Semantic block в `total-tech-debt-audit-main-current.md` частично обновлён (2026-09-26 refresh), но digest в `technical_debt_audit_registry.yaml` всё ещё от 2026-08-28 / commit `09ab9ac…`.

## Контролируемый остаток (не отдельные findings)

- Hotspot `budget_warnings`: **0**; duplication clusters: **0**
- Transition/sunset/expired compat: **0/0/0**; twin pairs: **0**
- Ruff/mypy/architecture_skip coarse budgets: **0**
- Config inconsistent parameters: **0**
- Маркеры TODO/FIXME в `src/bioetl`: **0** (единственное совпадение — строка `ADR-XXX` в валидаторе)
- `type: ignore` в src: **0**; `# noqa`: **1** файл

## Проверки

| команда | результат |
| --- | --- |
| `report-debt-governance-gates --check` | fail (3 gates) |
| `validate-technical-debt-audit --json` | fail |
| `test_issue_10595_composition_util_at_or_below_ceiling` | pass |

Machine output: `findings.json` (finding-v3 fingerprints).
