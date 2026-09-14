# Technical debt audit (full)

Дата: 2026-09-14
`prompt_id`: `prompt.audit.tech-debt`
`SCOPE`: `reports/quality/` `configs/quality/` `src/`
`MODE`: audit · `AUDIT_MODE`: full · `LANGUAGE`: ru
`REQUIRE_GH_TRACKING`: false
База: `origin/main` = `5c4243c9adad87f4a8eb4a6b0228e4b65841810e`

`surface_score`: **2** (scorecard/gates работают, exemptions=0, integral 9.14; freeze на потолке, leftover caps, stale remote-main pin)

## Метод

1. Регистры: `configs/quality/debt_scorecard.yaml`, ratchets, exemptions, constructor waivers, skip/assertless, shim/lazy inventories.
2. Evidence: `reports/quality/debt-governance-gates.json`, `architecture-quality-scorecard.json`, `hotspot-family-baseline.json`, `module-coverage-inventory.json`, `architecture-debt-remote-main-baseline.json`, `test-governance-current.json`, `total-tech-debt-audit-main-current.md`.
3. Сэмпл маркеров в `src/bioetl`: TODO/FIXME/HACK — 0; `type: ignore` / `noqa` / `pragma: no cover`.
4. Тренд vs budgets: over / at / under. **REJECTED_POLICY:** любой рост max_count / exemptions / hotspot caps.
5. Grafana/http WIP проигнорирован, кроме hash-only правки `module-coverage-inventory.json` в working tree.

## Тренд бюджетов (не предлагать повышение)

| Метрика | Live | Max | Target | Trend |
| --- | ---: | ---: | ---: | --- |
| architecture_metric_exemptions | 0 | 0 | 0 | at (Q3 met) |
| ruff/mypy/arch skip | 0 | 0 | 0 | at |
| transition/sunset/expired compat | 0/0/0 | 0 | 0 | at |
| uncovered/unmeasured modules | 0/0 | 0 | 0 | at |
| lazy_import | 77 | 77 | 60 | **at freeze** |
| private_import pairs | 15 | 15 | shrink | **at freeze** |
| config_count / unique_params | 27 / 419 | 27 / 419 | hold | **at freeze** |
| control_plane fan-in | 2 | 2 | hold | **at freeze** |
| runtime_builders fan-in | 3 | 3 | hold | **at freeze** |
| public export facades | 4 | 4 | hold | **at freeze** |
| composition modules | 295 | 300 | hold | under (5 slots) |
| factories files_ge_250_loc | 0 | 2 | 0 | **leftover under** |
| application_core fan-in | 5 | 7 | hold | leftover under |
| bootstrap fan-in | 2 | 3 | hold | leftover under |
| assertless_total_candidates | 88 | yaml 87 | 77 | **over yaml** |
| refined_assertless_tests | 0 | 0 | 0 | at |
| constructor waivers | 1 | shrink-only | 0 | at 1 |
| supporting_scripts zero-ref | 0 | 0 | 0 | at |
| flaky / uuid4 prod | 0 | 0 | 0 | at |
| debt-governance-gates snapshot | 45 pass | — | — | committed pass; live dirty fail |

Integral architecture quality: **9.14** (`good_targeted_improvements`). composition_di **6.0**. debt_burden **7.0**.

## Findings (10 PROVEN, P0/P1 = 0)

| ID | P | Наблюдение |
| --- | --- | --- |
| AUD-TD-001 | P2 | Stale remote-main pin 4aa9f5e7 vs origin/main 5c4243c9; gates snapshot 2465 vs inventory 2466 |
| AUD-TD-002 | P2 | Freeze cluster at cap (lazy/private/config/fan-in/facades) |
| AUD-TD-003 | P2 | Leftover hotspot caps (factories 2 vs live 0; core 7 vs 5; bootstrap 3 vs 2) |
| AUD-TD-004 | P2 | assertless yaml 87 < live 88; S9 не сравнивает live |
| AUD-TD-005 | P3 | Constructor waiver ×1 до 2026-12-31 |
| AUD-TD-006 | P3 | Total-tech-debt registry SHA 09ab9ac vs HEAD 5c4243c9 |
| AUD-TD-007 | P3 | Committed gates `budget_increase_count=not_evaluated_without_changed_from_ref` |
| AUD-TD-008 | P3 | 83 `type: ignore` (hotspot health startup ×11); TODO/FIXME нет |
| AUD-TD-009 | P3 | 15 xenon path exemptions, expiry 2026-12-31 |
| AUD-TD-010 | P3 | Lazy facade / shim review_by 2026-10-27 / 2026-10-21 |

Не считались долгом: 31 reviewed skip inventory (permanent_policy), grafana/http WIP, каждый TODO (их нет).

## Live check

Команда: `python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main`
exit 1: `module_coverage_scorecard_coherence`, `generated_artifact_drift` (`architecture_quality_scorecard`).

Причина fail: working tree сменил только `source_tree_sha256` в `module-coverage-inventory.json` (WIP http/grafana). HEAD-доказательство stale pin — AUD-TD-001.

## Paydown (shrink-only)

1. На чистом дереве re-pin remote-main baseline + gates `--update/--check --changed-from-ref origin/main`.
2. Снять ≥1 assertless candidate, чтобы live ≤ 87; привязать S9 к live. **Не** поднимать yaml.
3. Ratchet leftover: factories `files_ge_250_loc` 2→0; опционально core fan-in 7→5, bootstrap 3→2 при подтверждённом live.
4. Live-shrink freeze cluster (lazy к 60, private pairs) до любой фичи на этих швах.
5. Hygiene review shim/lazy до 2026-10-21/27; затем обновить total-tech-debt registry SHA.

## REJECTED_POLICY

- assertless `max_assertless_tests` 87→88
- lazy 77, private 15, config 27/419, fan-in 2/3, facades 4
- factories leftover держать 2 «на всякий случай»
- новые architecture_metric_exemptions / constructor waivers
- продление xenon expiry без сужения path_entries
