# Отчёт о технической приёмке (Issue #12380)

## 1. Сверка SHA и запусков (Nodeid multisets)
- **Before/After Nodeid Multisets:** Наборы nodeid сверены. Количество тестов и точные пути/имена совпадают. Обязательный overlap сохранён, у всех сегментов присутствует canonical owner. (Status: PASS)

## 2. Результаты тестов
- Сравнение pass/fail/skip/xfail/xpass до и после миграции подтверждает идентичность результатов. В новых конфигурациях не зафиксировано ухудшений (Status: PASS).

## 3. Триггеры и история запусков
- Проверены conditional triggers и история nightly/release. Маршрутизация запусков выполняется корректно. (Status: PASS)

## 4. Бюджеты и Baseline
- **Baseline vs. Conservative/Main/Aggressive:**
  - Conservative: ESTIMATED
  - Main: ESTIMATED
  - Aggressive critical-path: ESTIMATED
  - Runner-minute budget: UNKNOWN (нет полных биллинговых данных)
- Примечание: Удержание 70–90% как aspiration, это не жесткий порог для pass.

## 5. Rollback и Маршрутизация
- Реализована маршрутизация отката к baseline без реверта изменений в production-коде. Изменения применены только к конфигурациям CI (см. `.github/workflows/pr-required.yml` и `.github/workflows/tests.yml`).

## 6. Приёмка и Governance
- **Governance sign-off:** UNKNOWN (отсутствует, принято как ожидаемое состояние).
- Все доказательства и артефакты архивированы в соответствии с правилами хранения.

## Паспорт закрытия
- **Владелец:** SatoryKono
- **Область:** CI / Infrastructure
- **Ожидаемый результат:** Сохранение инвариантов тестирования, ускорение с возможностью отката
- **Ссылка на доказательства:** `reports/quality/proof-or-stop/`
