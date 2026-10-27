# PSC RF-004 — Domain I/O closeout + residue `#12477`

**Status:** keep / documented (не PASS fullsuite)  
**Issues:** [#12569](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12569) (RF-004),
[#12477](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12477) (residue OPEN),
[#12463](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12463) / [#12544](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/12544) (Variant A code on `main`)  
**RF-004 baseline tip (fresh `origin/main`):** `100854af874059f7a873a501518e2955f6eb5916`  
**Evidence land commit on `main`:** `#12564` → `100854af874059f7a873a501518e2955f6eb5916`  

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

На baseline tip: `python -m scripts.engineering.qa report-domain-io-taint-inventory --check`
→ exit 0, `violation_count=0`. Это **не** эквивалентно PASS полного
`tests/architecture` (`#12477`).

## 2. Residue `#12477` — не PASS (provenance счётчиков)

| Metric | Value |
| --- | --- |
| failed | **10** |
| passed | **5592** |
| skipped | **19** |

### 2.1. Какой SHA произвёл счётчики

Источник narrative: commit/PR **`#12564`** (Jules/Cursor body + squash
message на `main`).

| Role | Full SHA | Meaning |
| --- | --- | --- |
| **Run Base SHA** (заявлен в `#12564` как база прогона) | `1528cb5ac3d1adef0239df693b2a9a4573765bf2` | SHA, к которому текст `#12564` привязывает команду `uv run pytest tests/architecture/` и результат **10 / 5592 / 19** |
| **Land tip on `main`** (`#12564` merge) | `100854af874059f7a873a501518e2955f6eb5916` | Коммит, через который narrative evidence попал на `main`; `1528cb5a…` — ancestor этого tip |

**Атрибуция к tip `100854af87…`:** это **наследование / rebase land
evidence** через merge `#12564`, **не** утверждение, что RF-004 или PSC
выполнили fresh fullsuite re-run именно на tip `100854af87…` и получили те
же счётчики заново.

### 2.2. Журнал прогона

Путь `reports/issue-12477/20261027-alt1/` (логи / junit) **заявлен** в тексте
`#12564`, но **отсутствует** в tracked tree на tip `100854af87…` и на
исходных commits PR. In-tree run journal для сверки SHA **нет** — только
commit/PR narrative. Это усиливает статус **residue**, не PASS.

### 2.3. Verdict

**Итог:** evidence residue / **не** full PASS.  
**Owner waiver ≠ test PASS** — письменный acceptance или waiver **не**
превращает 10 failed в PASS. Issue `#12477` остаётся **OPEN** до фактического
зелёного fullsuite (exit 0 без неоговорённых skip/xfail) **на явно
зафиксированном full SHA с журналом** **или** явного owner out-of-scope с
пометкой `partially complete` на зависимых приёмках — без переписывания
счётчиков в PASS и без выдачи tip-inheritance за fresh green.

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
