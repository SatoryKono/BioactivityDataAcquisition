# Отчёт о технической приёмке (Issue #12380)

**Статус приёмки:** NOT COMPLETE — разделы 1–3 и 5 не имеют воспроизводимых доказательств; PASS снят.

**Контекст ревизий (этот отчёт):**

| Роль | SHA |
| --- | --- |
| Base (`origin/main` at report edit) | `2e5f70acf3df9b4b0e713098be5aeee2533618f8` |
| PR tip (report edit) | `20246c70409ea7c52ba0a5c6891d9e217ee678f2` |
| Prior merge tip | `0597395d65e4aa3daac482d96d467922ded50f23` |

PR: https://github.com/SatoryKono/BioactivityDataAcquisition/pull/12671  
Issue: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12380

## 1. Сверка SHA и запусков (Nodeid multisets)

- **Status: UNKNOWN**
- Нет сохранённого before/after сравнения nodeid multisets с командами, exit codes, base/head SHA прогонов и run IDs.
- В `reports/quality/proof-or-stop/` нет архива, привязанного к `#12380`.
- Доступен только текущий committed inventory (см. § «Измеренные артефакты») — это **не** before/after PASS.

## 2. Результаты тестов

- **Status: UNKNOWN**
- Нет воспроизводимого сравнения pass/fail/skip/xfail/xpass до и после миграции (команды, junit/артефакты, SHA-256, run IDs отсутствуют).

## 3. Триггеры и история запусков

- **Status: UNKNOWN**
- Conditional triggers и история nightly/release не подтверждены сохранёнными выгрузками / run IDs в этом PR.

## 4. Бюджеты и Baseline

- **Baseline vs. Conservative/Main/Aggressive:**
  - Conservative: ESTIMATED
  - Main: ESTIMATED
  - Aggressive critical-path: ESTIMATED
  - Runner-minute budget: UNKNOWN (нет полных биллинговых данных)
- Примечание: удержание 70–90% — aspiration, не порог pass. Числа без MEASURED-источника не повышают статус раздела.

## 5. Rollback и Маршрутизация

- **Status: UNKNOWN**
- Демонстрация отката к baseline routing **не** закрыта воспроизводимым evidence pack.
- На tip PR в `.github/workflows/pr-required.yml` остаётся **пустой stub** шага `impact-shadow-compare` (вызов `shadow-compare` и upload артефакта удалены; `id` и запись outcome сохранены). Судьба stub ждёт решения владельца — в этом отчёте stub **не** трактуется как завершённый rollback PASS.
- Ссылка на workflow без команд/run IDs/SHA артефактов не достаточна для PASS.

## 6. Приёмка и Governance

- **Governance sign-off:** UNKNOWN
- **Приёмка #12380:** NOT COMPLETE (не закрывать issue/PR по этому отчёту)
- Утверждение «все доказательства архивированы» **снято**: отдельного `#12380` архива в `reports/quality/proof-or-stop/` нет.

## Измеренные артефакты (supporting only; не закрывают §1–3/5)

Команды выполнены локально на tip `20246c70409ea7c52ba0a5c6891d9e217ee678f2`:

```text
.venv/bin/python -m scripts.engineering.qa.build_pytest_nodeid_inventory --check
# exit 0
# stdout: Inventory matches reports/quality/pytest-nodeid-inventory.json.

.venv/bin/python -m scripts.engineering.repo check-inventory --check \
  --manifest configs/quality/scripts_inventory_manifest.json
# exit 0
# INFO scripts=707 active=334 unknown=0 orphan=0 legacy=0

.venv/bin/python -m scripts.docs generate-cleanup-inventory --check
# exit 0
# [documentation-cleanup-inventory] inventory is synchronized
```

| Артефакт | Наблюдение | SHA-256 |
| --- | --- | --- |
| `reports/quality/pytest-nodeid-inventory.json` | `count=42972`, `unowned_count=0`, `duplicate_nodeids=[]`, `source_commit=0597395d65e4aa3daac482d96d467922ded50f23` | `6855af7aa54d7c838ea414961a48c9b1bc2226d2288c5d02ba7beb6bc1f5cb52` |
| `configs/quality/scripts_inventory_manifest.json` | `total_scripts=707` | `699d3a04e517501c7fd8682677fd6f8f21746bb91a878a1380dcc90177feae49` |

CI run IDs для полного before/after acceptance pack: **UNKNOWN** (на момент правки отчёта терминальный green exact-SHA evidence pack для #12380 не приложен).

## Паспорт закрытия

- **Владелец:** SatoryKono
- **Область:** CI / Infrastructure
- **Ожидаемый результат:** Сохранение инвариантов тестирования, ускорение с возможностью отката
- **Фактический результат этого документа:** evidence gap зафиксирован; приёмка **не** завершена
- **Ссылка на доказательства:** отсутствует dedicated `#12380` archive; см. таблицу measured artifacts выше
- **Открытые решения:** судьба empty `impact-shadow-compare` stub; сбор before/after nodeid/test/trigger/rollback evidence pack
