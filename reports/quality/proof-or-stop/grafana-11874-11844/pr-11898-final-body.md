HTTP retry fixtures теперь используют реальные response status, синхронный circuit-breaker state и virtual clock, согласованный с provider cooldown. Чрезмерный Retry-After завершает запрос по wait budget; cancellation отдельно проверяется при сохранённом cooldown и при допустимом повторе. CLI fixture сохраняет запрет независимых bounded extracts и проверяет явно связанный closed cohort. Зависимые quality artifacts пересчитаны каноническими генераторами без увеличения budgets/thresholds/exemptions.

Связано с #11874 и #11844; retirement/navigation исправлены ранее в #11894 и уже находятся в main.

Проверка:

- Полный canonical R11: 17/17 groups, producer `f9d20f27b43bc9cdc2b2dbd2d23aafce6fa94854`, production source SHA-256 `5115449e8c670f5393a58c7009693f666f0eff818fbaa80e0e9ea63f9827ae0f`; 32 256 PASS, 181 SKIP, 0 failures/errors; line 99.69%, branch 94.32%. Raw XML и все shard hashes/JUnit независимо проверены. Эта метрика относится к R11 producer, а не является новым full run на PR head.
- После R11 менялись только перечисленные fixture/marker/docstring test surfaces; supplemental owning suite на объединённой ветке: 141 PASS, 0 SKIP, 0 failures/errors. Production/QA source не менялся. Inventory содержит все 2548 модулей; historical primary XML и nonregressing additive provenance сохранены. 69 более высоких исторических значений явно обозначены в ledger и отдельном измеренном кандидате.
- Все шесть CI drift-family checks, module freshness/regression guards, navigation renderer для пяти UID, docs links/drift/cleanup и full-tree gate прошли; runtime AI sources не менялись, mirror sync не требуется.
- На чистом PR head `91a1443fe81dd5706d21c7fe0a5ae4b42741be42` обновлены пять native Chromium screenshot bundles с DOM/API parity и terminal-state receipts. Standard-directory preflight: `screenshots: ok`, source identity совпадает, Prometheus target UP.
- CI на точном PR head: `BLOCKED_EXTERNAL_PERMANENT`; 15 failed checks имеют account billing-lock annotation до старта. CI PASS не заявляется.

[Immutable acceptance evidence, XML/JUnit и PNG/tiles](https://github.com/SatoryKono/BioactivityDataAcquisition/tree/2d0c66aae1b895f47d511b178b8ded7f9cbe411e/reports/quality/proof-or-stop/grafana-11874-11844).

Полная live visual release acceptance остаётся false: #11895 сохраняет Overview Field-not-found и обрезанный Run Explorer TREE_MISSING; #11899 отдельно отслеживает исторические/current coverage расхождения. Failed/interrupted attempts сохранены отдельно и не комбинировались в R11 XML. `.env` не изменялся.
