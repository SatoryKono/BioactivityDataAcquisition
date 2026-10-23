BLOCKED: Выявлены существующие вызовы `core->scripts` в `src/bioetl/infrastructure/quality/`.
В соответствии с инструкцией: "При выявлении существующего core->scripts вызова зафиксировать BLOCKED и конкретный источник. Не добавлять scripts в runtime wheel и не обходить проверку."

Конкретные источники зависимости `core->scripts`:
1. `src/bioetl/infrastructure/quality/architecture_quality_scorecard.py`:
   - `from scripts.engineering.ci.validate_registry_dq_refs import build_diagnostics_payload as build_contract_registry_dq_diagnostics`
   - `from scripts.engineering.qa.report_adr_enforcement_matrix import build_payload as build_adr_enforcement_matrix`
   - `from scripts.engineering.qa.report_lazy_import_inventory import collect_lazy_imports`
2. `src/bioetl/infrastructure/quality/exemptions_registry_access.py`:
   - `from scripts.engineering.common.repo_paths import resolve_output_path`
3. `src/bioetl/infrastructure/quality/debt_scorecard.py`:
   - `from scripts.engineering.common.repo_paths import resolve_output_path`

Данный блокер не позволяет создать изолированный runtime wheel без включения пакета `scripts`, что запрещено политикой.
Требуется рефакторинг этих модулей перед тем как двигаться дальше.
