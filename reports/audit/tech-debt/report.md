# tech-debt

- prompt: `prompt.audit.tech-debt`
- surface_score: **1**
- proven: 7; P0/P1: 2
- run_id: `20260924T183653Z-9d9d303fa3f6-e28b4aa3`

На HEAD 4924a165 exemption-бюджет 0 и CI вызывает report-debt-governance-gates --check --changed-from-ref, но fail-fast полы hotspot-покрытия устарели и тест их не роняет: control plane 113 модулей при поле 124, bootstrap 45 при поле 50. source_tree_sha256 расходится у inventory, scorecard и debt-governance-gates, хотя снимок гейтов помечен pass. Потолки без запаса: конфиги 27/27 и параметры 419/419, retirement 18/18, cast(Any) 142/142, files≥250 adapter 2/2 и composite 1/1. В src/bioetl нет файлов длиннее 500. Бюджеты не повышать.

## Findings

- **TD-001** P1 PROVEN `configs/quality/debt_scorecard.yaml:748` — Fail-fast полы hotspot-покрытия ниже живого measured count не блокируют архитектуру: тест принимает вычисленный threshold_status=fail.
- **TD-002** P1 PROVEN `reports/quality/debt-governance-gates.json:49` — Зафиксированный pass-снимок source_tree_sha256 не воспроизводится по текущим входам гейта связности.
- **TD-003** P2 PROVEN `src/bioetl/application/services/quality/data_quality_anomalies.py:21` — Неоправданные cast(Any) сидят ровно на shrink-only потолке и маскируют отсутствие Protocol-host.
- **TD-004** P2 PROVEN `configs/quality/debt_scorecard.yaml:259` — Поверхность конфигов и словарь параметров заморожены на current_count=max_count без запаса.
- **TD-005** P2 PROVEN `configs/quality/debt_scorecard.yaml:900` — Классифицированный retirement-остаток и zero-import кандидаты стоят на потолке.
- **TD-006** P2 PROVEN `configs/quality/debt_scorecard.yaml:770` — Семейные бюджеты files_ge_250_loc заняты целиком живыми модулями.
- **TD-007** P2 PROVEN `configs/quality/debt_scorecard.yaml:159` — Потолок публичных фасадов зафиксирован текущим счётчиком, а не отдельным max_count; growth-гейт берёт лимит из того же счётчика scorecard.

## Remediations

- В test_hotspot_refactor_targets_have_authoritative_module_coverage_gates требовать threshold_status=pass и вернуть measured count к полям 124 и 50, не снижая percent-полы и не поднимая max_count.
- Пересобрать architecture-quality-scorecard и debt-governance-gates от текущего module-coverage-inventory, чтобы три source_tree_sha256 совпали, без изменения лимитов.
- Заменить PD4 cast(Any, None) на Protocol-host и снижать max_unjustified_count только вниз от 142.
- Расширение config surface или files≥250 компенсировать сжатием в том же изменении; max_count 27/419 и files_ge_250_loc 2/1 не поднимать.
- Ввести независимый shrink-only max_count для public_export_facade_count и public_entrypoint_count; текущие 3 и 12 не повышать.
