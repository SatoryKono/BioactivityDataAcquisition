# #10186 — проверяемое происхождение renders

Source итогового capture: `a1533745a1ce7647f6a1fe55d12741e25bda1982`. Исправления: PR #10236, #10239 и #10240.

| Пакет | ZIP SHA-256 | Immutable manifest SHA-256 |
|---|---|---|
| [reviewer-final-a1533745a1ce.zip](./reviewer-final-a1533745a1ce.zip) | `a3af00156666af2e12a1d0ed3c6462b6c4b945b276ea94c6df4292e72b5afd8e` | `9daa8be78d574b50f355a7ba3c1b09dd8c7f20365d6686763f1e02a747860438` |
| [reviewer-layout-10165.zip](./reviewer-layout-10165.zip) | `5dfb0926eafc4853cdd8d2aeebebb8c879c3b4259d511069a5a34b6fd52eb159` | `fd7291c26cd71e162b69fafb30d593252a8502c8ceb476435efef48797e70746` |

Оба пакета независимо прошли provenance 7/7: commit → source JSON → provisioned/browser-loaded model → browser context → PNG. Пакет #10165 закреплён за `e8d64ddbf867dba8310fecf4572cd88909eb47eb` и содержит Git bundle этого source. Контексты двух capture не смешиваются.

Финальный capture: 1366×768, dark, 100%, kiosk off, collapsed rows; фиксированное окно 2026-09-08 00:00–06:00 UTC. Полные variables, physical/CSS viewport, DSF, browser version, chrome/zoom и модели before/loaded/after находятся в immutable manifest.

32/32 контроля integrity дали ожидаемый результат. 31 повреждение/подмена отвергнуты; перемещение mutable latest сохранило PASS явно выбранного immutable manifest. После распаковки ZIP повторно проверены все file hashes, CRC и provenance 7/7.

Historical pack: **REJECTED**. Trust/DQ/Overview не совпали с исходными hashes; совпадающие оригиналы не найдены среди 8378 доступных PNG в 197 evidence-каталогах из 181 worktree. Ошибок чтения нет. Root cause **UNKNOWN**, исходные hashes сохранены. Подробности: [historical-provenance-review.json](./historical-provenance-review.json).

На итоговом SHA: 148 тестов PASS; governance/docs/debt PASS; CI ADMIT и все применимые main workflows успешны. Один scripts-catalog тест пропущен по штатному Windows guard, Linux CI покрывает эту проверку. Runtime mirrors не менялись, documentation drift отсутствует, бюджеты не увеличены. Защищённая публикация Docker-образа остаётся отдельным ожидающим действием.

Это приёмка происхождения. Layout, contrast, reflow и correctness чисел имеют отдельные verdicts. Финальный viewport capture сохраняет layout FAIL для панелей вне первого экрана; renderer exit code 1 не превращён в PASS.

В final ZIP включены инструкции воспроизведения, CI attestation, validation receipts, исходные JSON, historical evidence, таблица negative controls и подтверждение 30 одобренных удалений episodic notes. Резервные ZIP с содержимым заметок остаются локально.

Передача evidence: #10165, #10170, #10185. Индексы ZIP: [final-index.json](./final-index.json), [layout-index.json](./layout-index.json). Ссылки при приёмке должны быть закреплены за полным Git commit SHA этого пакета.
