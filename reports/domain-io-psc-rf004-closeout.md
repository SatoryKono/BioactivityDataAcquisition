# PSC RF-004 — Domain I/O closeout + residue `#12477`

**Status:** keep / documented (не PASS fullsuite)  
**Issues:** [#12569](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12569) (RF-004),
[#12477](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12477) (residue OPEN),
[#12463](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12463) / [#12544](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/12544) (Variant A code on `main`)  
**Baseline tip (fresh `origin/main`):** `100854af874059f7a873a501518e2955f6eb5916`  
**Evidence commit (fullsuite rerun):** `#12564` @ same tip SHA  

## 1. Variant A (Domain I/O) — зафиксированная норма PSC

Код **Variant A** (operation-based Domain I/O: запрещены I/O-вызовы, чистые
`urllib.parse` / `PurePath` разрешены) уже на `main` через `#12544`
(`6e6e8c56dc`). RF-004 **не** переигрывает выбор A vs B из старого draft PR
text и **не** меняет scanner semantics.

Для трека Policy Schema Cleanup (PSC) Variant A принимается как **landed /
accepted Domain I/O surface norm**. SSOT политики:

- норма: `docs/02-architecture/01-domain-layer.md` §3
- CI inventory: `scripts/engineering/qa/report_domain_io_taint_inventory.py`
- артефакт: `reports/quality/domain-io-taint-inventory.json`
- owning tests: `tests/architecture/test_domain_io_taint_inventory.py`

На baseline tip: `violation_count=0`; inventory `--check` зелёный. Это **не**
эквивалентно PASS полного `tests/architecture` (`#12477`).

## 2. Residue `#12477` — не PASS

По `#12564` / tip `100854af874059f7a873a501518e2955f6eb5916` полный прогон
`tests/architecture`:

| Metric | Value |
| --- | --- |
| failed | **10** |
| passed | **5592** |
| skipped | **19** |

**Итог:** evidence residue / **не** full PASS.  
**Owner waiver ≠ test PASS** — письменный acceptance или waiver **не**
превращает 10 failed в PASS. Issue `#12477` остаётся **OPEN** до фактического
зелёного fullsuite (exit 0 без неоговорённых skip/xfail) **или** явного
owner out-of-scope с пометкой `partially complete` на зависимых приёмках —
без переписывания счётчиков в PASS.

## 3. Named blocker `#12464` ← `#12477`

Файл `reports/NAMED_BLOCKER_12464.md`: **KEEP** (не retire).

CI-приёмка `#12464` остаётся pending, пока `#12477` не даст совместимое
fullsuite evidence, принятое владельцем. Узкий Domain I/O inventory green
**не** снимает этот blocker.

## 4. Owner path (residue)

1. Триаж **10 failed** nodeid из evidence `#12564` / `#12477`.
2. Повторный полный `tests/architecture` на целевом SHA → exit 0.
3. Закрытие `#12477` только с паспортом закрытия issue (SHA, команды,
   exit codes, независимый проверяющий).
4. После принятого green evidence — reconcile `NAMED_BLOCKER_12464.md`
   (retire) и зависимых CI-приёмок (`#12464` и связанные).
5. До п.3–4: blocker **KEEP**; не заявлять PASS из waiver.

## 5. RF-004 explicit non-goals

- Нет смены scanner / Domain I/O semantics.
- Нет RF-001/RF-002 `extra=forbid` работы.
- Нет `.env` правок; нет увеличения tech-debt budgets.
- Нет ad-hoc fullsuite как auto-step этого PR (owning = domain-io inventory).
