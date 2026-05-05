# CI Failure Triage — 2026-05-05

Источник: GitHub Actions API (public) по репозиторию `SatoryKono/BioactivityDataAcquisition`.

## Приоритетные workflow/jobs

| Job | Run / Job URL | First failing step | First error (1–3 строки) | Failure type |
|---|---|---|---|---|
| `smoke-check` | https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/25351874415/job/74333040670 | `Validate VCR metadata stale-age policy` | `Node.js 20 actions are deprecated ... actions/cache@v4, actions/setup-python@v5 ...` | **policy gate** |
| `lint` | https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/25351597889/job/74332193941 | `Ruff format (strict full gate - src + tests)` | `Node.js 20 actions are deprecated ... actions/cache@v4, actions/setup-python@v5 ...` | **policy gate** |
| `type-check` | https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/25351874419/job/74333040740 | `Run mypy (strict mode, full gate)` | `Node.js 20 actions are deprecated ... actions/cache@v4, actions/checkout@v4, actions/setup-python@v5 ...` | **policy gate** |
| `governance-preflight` | https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/25351874415/job/74333040646 | `Validate scripts inventory + lifecycle governance` | `Node.js 20 actions are deprecated ... actions/cache@v4, actions/setup-python@v5 ...` | **policy gate** |
| `matrix-smoke-blocking` | https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/25351874406/job/74333040671 | `Checkout code` | `Node.js 20 actions are deprecated ... actions/upload-artifact@v4 ...` | **policy gate** |

## Группировка по общей причине

### Причина A (массовая): Node.js 20 deprecation policy warning аннотируется как failing annotation
- Одна и та же причина одновременно видна в нескольких blocking jobs (`smoke-check`, `lint`, `type-check`, `governance-preflight`, `matrix-smoke-blocking`).
- По факту это **policy gate** (platform/runtime policy), а не test assertion и не external service outage.
- Практический эффект: один policy issue может «уронить» сразу серию jobs в разных workflow.

## Что это не похоже на
- `bootstrap` (`setup-python-uv`/`uv sync`) — нет признаков первичного падения именно на bootstrap шаге в зафиксированных first failing steps.
- `test assertion` — в first failing evidence нет stacktrace/assertion, только policy-deprecation annotation + `Process completed with exit code 1`.
- `external service` — не видно сетевых/внешних API отказов в первом surfaced error.


## RCA и remediation plan (updated 2026-05-05)

- Корневая причина: workflows и composite action использовали `actions/*` refs на runtime Node 20-era (`upload-artifact@v4`, `setup-python@v5`, `cache@v4`, частично `checkout@v4`), что блокируется новой policy GitHub.
- Решение: унифицировать policy на **pinned commit SHA** для runtime-sensitive actions во всех `.github/workflows/*.yml` и `.github/actions/setup-python-uv/action.yml`.
- Целевые pinned refs:
  - `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd` (v6)
  - `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065` (v5)
  - `actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830` (v4)
  - `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02` (v4)
- Governance guardrail: добавить pre-merge проверку `python -m scripts.engineering.repo check-actions-runtime-policy`; блокировать непинованные или non-vetted refs.
