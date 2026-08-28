#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile


def gh_token():
    return (
        os.environ.get("CODEX_GITHUB_PERSONAL_ACCESS_TOKEN")
        or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        or os.environ.get("GH_TOKEN")
        or ""
    )


def create_issue(title, body, labels):
    tok = gh_token()
    env = {**os.environ, "GH_TOKEN": tok, "PYTHONIOENCODING": "utf-8"}
    payload = json.dumps({"title": title, "body": body, "labels": labels}, ensure_ascii=False)
    tf = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8")
    tf.write(payload)
    tf.close()
    r = subprocess.run(
        ["gh", "api", "repos/SatoryKono/BioactivityDataAcquisition/issues", "--input", tf.name],
        capture_output=True,
        text=True,
        env=env,
        encoding="utf-8",
        errors="replace",
    )
    os.unlink(tf.name)
    print("TITLE:", title[:80])
    if r.stdout:
        print("STDOUT:", r.stdout[:2500])
    if r.stderr:
        print("STDERR:", r.stderr[:800])
    print("---")
    if r.stdout:
        try:
            j = json.loads(r.stdout)
            print("CREATED #", j.get("number"), j.get("html_url"))
            return j.get("number"), j.get("html_url")
        except Exception as e:
            print("parse error", e)
    return None, None


ISSUES = [
    (
        "[Security][PR-1] RF-001 — Воспроизводимый security baseline (Trivy/CodeQL/Scorecard)",
        """### Контекст
Срез 27.08 (90c806f0b1): 112 alerts выше Low (4C+31H+77M). Актуализация 28.08 по API (GH_TOKEN gho_G3fA..., security_events:read): **217 open** — Trivy 181, CodeQL 9, Scorecard 21, zizmor 6. Trivy M+H+C: **83** (4C+19H+60M) + 67L+31U. Workflow `docker.yml` сейчас `severity: CRITICAL,HIGH` и теряет Medium.

Цель RF-001 — сделать данные сканирования воспроизводимыми **до** правок кода, чтобы последующие PR имели точку отсчёта.

### Scope
- `.github/workflows/docker.yml` — расширить `severity` до `CRITICAL,HIGH,MEDIUM` (и `UNKNOWN` для наблюдаемости)
- `Dockerfile.bioetl` — зафиксировать digest с provenance (python 3.12.14, 2026-08-16, sha256:a11651...)
- `uv.lock` / `pyproject.toml` — зафиксировать `pip --version`, `uv pip freeze`

### Задачи
- [ ] В ветке `chore/security-baseline-20260828` без изменения кода приложения воспроизвести baseline
- [ ] Сохранить `reports/security/trivy-results.sarif`, `bioetl-ghcr.spdx.json`, таблицу `alert_number,CVE,package,installed,fixed,layer,status`
- [ ] Проверить последние runs CodeQL (`codeql.yml`) и Trivy (`docker.yml:docker-build`) — оба зелёные до старта RF-002
- [ ] Обновить `docker.yml` severity → `CRITICAL,HIGH,MEDIUM` (оба Trivy job)

### Acceptance Criteria
- [ ] PR-1 содержит SARIF/SBOM/CSV + ссылки на успешные workflow runs
- [ ] `trivy image --severity CRITICAL,HIGH,MEDIUM` воспроизводим локально и в CI
- [ ] Зафиксированы `python --version`, `pip --version` в `/app/.venv`, `uv pip freeze`

### Связи
- План: `reports/plans/security-remediation-2026-08-28.md` § RF-001
- Блокирует: PR-2 (RF-002)
- Alerts: все Trivy (косвенно), CodeQL/Scorecard baseline

### Риски
Неблокирующий. Может выявить исторические Medium (scanner version). Источник истины — вновь загруженный SARIF с фиксацией scanner DB/version/digest.
""",
        ["security", "priority:high", "ci/cd", "governance"],
    ),
    (
        "[Security][PR-2] RF-002 — Устранить 83 Trivy findings из Docker image (4C+19H+60M)",
        """### Контекст
Актуализация 28.08: Trivy **83** выше Low (4C+19H+60M; всего 181 с LOW 67 + UNKNOWN 31). Топ-пакеты: `perl-base 13 (4C+4H+5M)`, `libc6/libc-bin 4-5M+1H`, `util-linux/mount/libmount1/libuuid1/libsmartcols1/liblastlog2-2/bsdutils 4-7`, `libsqlite3-0 6`, `tar 5`, `pip 5 (MEDIUM 4 + LOW 1)`, `libsystemd0/libudev1 5`, `coreutils 4`. `uv.lock` уже `pip 26.1.2`, но образ показывает `pip 25.0.1` в `/app/.venv`.

### Scope
- `Dockerfile.bioetl` (оба stage FROM `python@sha256:a116...`), `uv.lock`/`pyproject.toml` при необходимости
- `.github/workflows/docker.yml` scan policy

### Задачи
- [ ] Обновить Python/Debian image digest на свежий `python:3.12-slim-bookworm` с provenance-комментарием
- [ ] Явно обновить pip в `/app/.venv` после `uv sync` до `26.1.2` (Trivy-fixed), проверить `pip --version` внутри образа
- [ ] `docker build --no-cache` + `trivy image --severity CRITICAL,HIGH,MEDIUM --format sarif`
- [ ] Для CVE без fixed version: смена базы/удаление пакета из runtime (если не нужен для entrypoint/healthcheck). `ignore-unfixed` / широкий `.trivyignore` запрещены
- [ ] Для неустранимого CVE — отдельный issue с владельцем, expiry, exposure-анализом (не закрывает риск)

### Acceptance Criteria
- [ ] Скан нового образа `bioetl:${sha}`: 0 Critical/High/Medium либо каждый residual с утверждённым исключением и планом removal
- [ ] `SBOM` приложен, `non-root USER 999`, `bioetl health server` OK, `docker compose config` валиден, smoke pipeline зелёный
- [ ] Rollback — возврат к прежнему immutable digest без публикации уязвимого `latest`

### Связи
- Зависит от: PR-1
- План: RF-002
- Alerts: Trivy 83 (CRITICAL 4: perl-base ×4; HIGH 19: bsdutils, gzip, libacl1, libblkid1, liblastlog2-2, libmount1, libncursesw6, libsmartcols1, libtinfo6, libuuid1, login, mount, ncurses-base/bin, util-linux; MEDIUM 60 — см. тело)

### Evidence
Before/after counts, digest, workflow URLs, SBOM/SARIF, `pip --version` внутри образа.
""",
        ["security", "priority:high", "ci/cd", "docker"],
    ),
    (
        "[Security][PR-3] RF-003 — Исправить ReDoS в _redaction.py (CodeQL #1121, #1122)",
        """### Контекст
CodeQL `py/redos` error ×2 в `src/bioetl/domain/exceptions/_redaction.py:26-29` — `_INLINE_SECRET`:
`"(?:\\\\.|[^\"])*"` пересекается с `[^"]` (backslash входит в оба), экспоненциальный backtracking на `\\\\\\\\...`.

### Scope
- `src/bioetl/domain/exceptions/_redaction.py:26-29` — только Domain, без I/O и межслоевых импортов

### Задачи
- [ ] Заменить `"(?:\\\\.|[^\"])*"` → `"(?:[^\"\\\\]|\\\\.)*"` и аналогично для `'` (`"(?:[^'\\\\]|\\\\.)*"`)
- [ ] Дополнить `tests/security/test_exception_redaction.py`, `tests/security/test_structured_logging_redaction.py`, `tests/unit/domain/test_arch_cr_remediation_6461.py`:
  - [ ] redaction обычных `token/password` values
  - [ ] escaped quotes, malformed input
  - [ ] adversarial `\\\\` × десятки тысяч с bounded `pytest-timeout` (не wall-clock сравнение)
- [ ] Прогнать `mypy --strict`, architecture gates, CodeQL

### Acceptance Criteria
- [ ] CodeQL `py/redos` #1121, #1122 отсутствуют после анализа
- [ ] Positive/negative redaction coverage, отсутствие регрессии секретов при неверной границе quoted value
- [ ] Изменение остаётся в Domain

### Связи
- План: RF-003, `reports/plans/security-remediation-2026-08-28.md`
- Alerts: CodeQL #1121, #1122 (`py/redos`, error)

### Риск
Раскрытие секрета при неправильной границе — обязателен полный coverage.
""",
        ["security", "priority:high", "domain"],
    ),
    (
        "[Security][PR-4] RF-004…RF-007 + RF-010 — Script/Test SAST и WSL proxy (CodeQL #32, #129, #247, #509, #1181-1183 + zizmor ×6)",
        """### Контекст
CodeQL 7 находок + zizmor 6:
- `py/bad-tag-filter` warning ×3 — #1183 `prune_orphan_nodes.py:101`, #1182/#1181 `generate_all_bundles.py` (литерал `-->` распознаётся как HTML-comment filter, хотя парсит Mermaid DSL)
- `py/clear-text-logging-sensitive-data` error #509 — `check_replay_preflight.py:223` `print(json.dumps(report))` с taint от `_secret_filter_status`
- `py/incomplete-url-substring-sanitization` warning #32 `test_chembl.py`, #247 `test_idmapping_client.py` (`in` вместо точной валидации)
- `py/bind-socket-all-network-interfaces` error #129 — `wsl_proxy.py:20` `LISTEN_HOST=0.0.0.0:3128`
- `zizmor/template-injection` error ×6 — `docs.yml ×4`, `architecture-governance-cache/action.yml ×2`

### Scope
- `scripts/diagrams/fix/prune_orphan_nodes.py:101-116`, `scripts/diagrams/render/generate_all_bundles.py:228`
- `scripts/engineering/qa/vcr/check_replay_preflight.py:101-223`
- `tests/integration/adapters/test_chembl.py`, `tests/unit/infrastructure/adapters/uniprot/test_idmapping_client.py`
- `scripts/ops/runtime/wsl/wsl_proxy.py:20`
- `.github/workflows/docs.yml`, `.github/actions/architecture-governance-cache/action.yml`

### Задачи
- [ ] RF-004 Mermaid: убрать литерал `-->` из regexp (напр. `\\x3e` или конкатенация), сохранить грамматику; параметризовать `-->, <--, ==>, -.->, --o, --x, ~~~`, негативный `--!>`
- [ ] RF-005 VCR: отделить внутренний result от public DTO (только `schema_version`, counts, bool sanitizer_status, blocker ids, repo-relative paths); запретить `headers/query/payload/callback/absolute paths`; переименовать `secret_filter`→`sanitizer_status`
- [ ] RF-006 URL: заменить `in` на `urlsplit` exact `scheme/hostname/path` или exact constant; найти production redirect consumer — при недоверенном redirect добавить allowlist
- [ ] RF-007 WSL: `LISTEN_HOST` `0.0.0.0`→`127.0.0.1`, opt-in `0.0.0.0` только с CIDR allowlist + firewall rule + unit-тестируемая валидация
- [ ] RF-010 zizmor: вынести `${{ github.* }}` из `run:` в `env:`/`inputs`, добавить санитизацию; включить `zizmor` в required checks
- [ ] Тесты: `test_diagram_bundle_generator_contracts.py`, `test_diagram_tooling_fail_closed.py`, `test_vcr_replay_preflight.py` (sentinel secret не в stdout), URL negative tests

### Acceptance Criteria
- [ ] CodeQL #1181-1183, #509, #32, #247, #129 отсутствуют либо узкий approved dismiss с тестами/доказательством
- [ ] zizmor 6 отсутствуют
- [ ] Все targeted tests зелёные, `ruff`/`mypy`/architecture gates зелёные

### Связи
- План: RF-004…RF-007, RF-010
- Alerts: CodeQL #1181, #1182, #1183, #509, #32, #247, #129; zizmor #1266-1271
""",
        ["security", "priority:high", "ci/cd"],
    ),
    (
        "[Security][PR-5] RF-008 — GitHub ruleset и review governance (Scorecard #1272, #1295, #1296)",
        """### Контекст
Scorecard 28.08: `BranchProtectionID` #1272 (нет ruleset для `main`), `CodeReviewID` #1295 (0/25 approved changesets), `CIIBestPracticesID` #1296. Всего Scorecard 21 (включая PinnedDependencies ×16, Fuzzing). Это внешнее изменение, способное заблокировать merge-процессы — требует отдельной авторизации владельца.

### Scope
- GitHub repository settings → Ruleset для `main` (не код)

### Задачи
- [ ] Создать/обновить ruleset `main`: запрет direct pushes/force pushes/delete, обязательный PR, минимум 1 approving review, dismiss stale approvals, conversation resolution, required status checks, restrict bypass только maintainers, require linear history (при совместимости)
- [ ] Согласовать с владельцем список required checks и bypass actors **до** применения
- [ ] Dry-run PR: подтвердить required checks и ≥25 approved changesets в последующих Scorecard runs
- [ ] Экспорт ruleset (screenshot/JSON) в evidence

### Acceptance Criteria
- [ ] Ruleset активен, `main` защищена, Scorecard #1272 и #1295 закрыты (SARIF чист)
- [ ] Нет lockout существующих merge-процессов; rollback — documented opt-in, не возврат `0.0.0.0`
- [ ] Owner approval зафиксирован в issue/PR

### Связи
- План: RF-008
- Alerts: Scorecard #1272 `BranchProtectionID`, #1295 `CodeReviewID`, #1296 `CIIBestPracticesID`
- Блокирует: PR-6 (Scorecard closeout)

### Риск
Высокий — блокировка мёрджа. Не объединять с code changes.
""",
        ["security", "priority:high", "ci/cd", "governance"],
    ),
    (
        "[Security][PR-6] RF-009+RF-011 — Supply-chain closeout: PinnedDependencies ×16 + Vulnerabilities 56 OSV + финальная верификация",
        """### Контекст
Scorecard 28.08: `PinnedDependenciesID` ×16, `VulnerabilitiesID` #1294 (56 OSV/GHSA — агрегация, частично пересекается с Trivy 83), `FuzzingID` #1277. Дубликаты с RF-002 должны иметь одну карточку remediation. Закрытие только после повторного Scorecard run.

### Scope
- Все незапиненные экшены/образы (`.github/workflows/*.yml`, `.github/actions/**`, `Dockerfile.bioetl`)
- `uv.lock` / `pyproject.toml` / `Dockerfile.bioetl` для Python и OS зависимостей
- SBOM + audit outputs

### Задачи
- [ ] PinnedDependencies: запинить все Actions по SHA с комментарием `# vX.Y.Z` (Dependabot/Renovate), проверить `hadolint`/`actionlint`
- [ ] Vulnerabilities: сформировать SBOM + `uv audit`/`pip-audit` для `uv.lock` и runtime image; сопоставить каждый из 56 OSV → `package→manifest/image→fixed version→owner` (матрица)
- [ ] Для `fixed version` — обновить минимальный диапазон, `uv lock --upgrade`, hashes, прогнать targeted API/contract tests
- [ ] Для `dev-only` — оценить удаление из dependency graph или отдельное обновление
- [ ] RF-011 финальная верификация:
  - [ ] Контейнер: clean rebuild, `trivy image --severity CRITICAL,HIGH,MEDIUM --format sarif`, SBOM, `pip --version` в образе
  - [ ] SAST: зелёный CodeQL + zizmor, отсутствуют #32/#129/#247/#509/#1121-1122/#1181-1183 либо узкий dismiss
  - [ ] Quality: `ruff check/format --check`, `mypy --strict --no-incremental src/bioetl`, `check-exemptions`, `test_quality_debt_scorecard.py`, `test_regression_metrics.py`
  - [ ] Governance: ruleset export, защищённый PR, новый Scorecard SARIF, список required checks + bypass policy

### Acceptance Criteria
- [ ] Scorecard PinnedDependencies ×16 и Vulnerabilities (#1294) закрыты после повторного workflow run
- [ ] Trivy/Scorecard/CodeQL результаты reconciled, alerts закрыты **только** с proof (SARIF/SBOM/workflow URLs)
- [ ] В каждом PR evidence block: before/after counts, commit/digest, workflow URLs, gates, отсутствие роста техдолга, residual risks
- [ ] Если CVE без patch — exception issue с владельцем/expiry/exposure, не ложный green

### Связи
- Зависит от: PR-2 (RF-002) + PR-5 (RF-008)
- План: RF-009, RF-011
- Alerts: Scorecard #1294 Vulnerabilities (56 OSV), PinnedDependencies ×16, FuzzingID; Trivy дубликаты

### Evidence
SBOM, audit outputs, матрица OSV, workflow links, governance export.
""",
        ["security", "priority:high", "ci/cd", "governance"],
    ),
]

for title, body, labels in ISSUES:
    create_issue(title, body, labels)
