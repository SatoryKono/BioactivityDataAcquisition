# GitHub Workflow Визуализация для BioETL

## Feature Development Flow

```mermaid
graph TD
    A[Начало] --> B[git switch main]
    B --> C[git fetch --prune origin]
    C --> D[git pull --ff-only]
    D --> E[git switch -c feat/название]
    E --> F[Разработка + тесты]
    F --> G{make lint && make test OK?}
    G -->|Нет| F
    G -->|Да| H[git commit]
    H --> I[git fetch origin]
    I --> J[git rebase origin/main]
    J --> K{Конфликты?}
    K -->|Да| L[Разрешить конфликты]
    L --> J
    K -->|Нет| M[git push -u origin HEAD]
    M --> N[gh pr create]
    N --> O[CI Checks]
    O --> P{All checks green?}
    P -->|Нет| Q[Исправить]
    Q --> F
    P -->|Да| R[Code Review]
    R --> S{Needs changes?}
    S -->|Да| T[Внести изменения]
    T --> F
    S -->|Нет| U[PR Approved]
    U --> V[Squash & Merge]
    V --> W[git switch main]
    W --> X[git pull --ff-only]
    X --> Y[git branch -d feat/название]
    Y --> Z[Конец]
```

## CI Pipeline Structure

```mermaid
graph TB
    START[workflow_call] --> DEP[dependency-preflight]
    START --> CONFIG[config-schema-preflight]

    DEP --> SMOKE[smoke-check]
    DEP --> GOV[governance-preflight]
    DEP --> FAST[test-fast]
    DEP --> MATRIX[test-matrix]
    DEP --> E2E[control-plane-e2e]
    DEP --> CONTRACT[contract-confidence]
    DEP --> TRACKD[track-d-gates]
    DEP --> MEMORY[memory-tests]
    DEP --> PERF[performance-budgets]
    DEP --> QM[quality-metrics-gate]

    GOV --> DQ[dq-consistency-gate]

    SMOKE --> COV[coverage-verify]
    FAST --> COV
    MATRIX --> COV
    CONTRACT --> COV

    CONTRACT --> DURATION[duration-telemetry]
    TRACKD --> DURATION
    FAST --> DURATION
    MATRIX --> DURATION
    MEMORY --> DURATION

    style START fill:#e1f5ff
    style DEP fill:#fff9c4
    style COV fill:#fff59d
```

Рёбра совпадают с ключами `needs` в `.github/workflows/tests.yml` для jobs на схеме. `dependency-preflight` и `config-schema-preflight` не объявляют `needs`. `coverage-verify` также ждёт `repo-backed-unit`, `unit-scripts-tooling`, `unit-filesystem-contracts`, `unit-subprocess-backed` и `serial-coverage`. `duration-telemetry` также ждёт `flaky-telemetry`, `repo-backed-unit`, `serial-coverage` и те же `unit-*` jobs.

## PR Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft: gh pr create --draft
    Draft --> Open: Mark ready for review
    Open --> InReview: Reviewer assigned
    InReview --> ChangesRequested: Issues found
    InReview --> Approved: Looks good
    ChangesRequested --> Open: Changes pushed
    Approved --> CI_Running: Auto checks
    CI_Running --> CI_Failed: Check failed
    CI_Running --> CI_Passed: All checks green
    CI_Failed --> Open: Fix and push
    CI_Passed --> Merged: Squash & merge
    Merged --> [*]: Branch deleted
```

## Issue Triage Flow

```mermaid
graph LR
    A[New Issue] --> B{Type?}
    B -->|Bug| C[Label: bug]
    B -->|Feature| D[Label: enhancement]
    B -->|Question| E[Label: question]
    
    C --> F{Priority?}
    D --> F
    E --> F
    
    F -->|Critical| G[Label: critical]
    F -->|High| H[Label: high]
    F -->|Medium| I[Label: medium]
    F -->|Low| J[Label: low]
    
    G --> K[Immediate action]
    H --> L[This sprint]
    I --> M[Next sprint]
    J --> N[Backlog]
    
    K --> O[Assign developer]
    L --> O
    M --> P[Sprint planning]
    N --> Q[Triage regularly]
```

## Release Workflow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant CI as GitHub Actions
    participant TestPyPI as TestPyPI

    Dev->>CI: workflow_dispatch release.yml
    Note over Dev,CI: dry_run defaults to true
    par
        CI->>CI: build wheel and sdist on Python 3.13
        CI->>CI: test-install from the local wheel
    and
        CI->>CI: security-gate
    and
        CI->>CI: release-tests on Python 3.13
    end
    alt dry_run is false
        CI->>TestPyPI: publish-testpypi test.pypi.org/legacy
    else dry_run is true
        CI->>CI: build only
    end
```

`release.yml` запускается только через `workflow_dispatch`. `test-install` ждёт `build` и ставит локальное wheel. `security-gate` и `release-tests` не объявляют `needs`. `publish-testpypi` ждёт `build`, `test-install`, `security-gate` и `release-tests` и публикует в `https://test.pypi.org/legacy/` только при `dry_run=false`.

## Dependabot Weekly Triage

```mermaid
graph TD
    A[Начало недели] --> B[gh pr list --label dependencies]
    B --> C{Для каждого PR}
    C --> D{Тип обновления?}
    D -->|Security High/Critical| E[Приоритетный review]
    D -->|Major version| F[Тщательный review]
    D -->|Minor/Patch| G[Быстрый review]
    
    E --> H{CI green?}
    F --> I{Breaking changes?}
    G --> H
    
    H -->|Да| J[Merge немедленно]
    H -->|Нет| K[Investigate failure]
    
    I -->|Нет| H
    I -->|Да| L[Migration plan]
    
    K --> M[Fix или close PR]
    L --> N[Schedule for sprint]
    
    J --> O{Ещё PRs?}
    M --> O
    N --> O
    
    O -->|Да| C
    O -->|Нет| P[Конец недели]
```

## CI Troubleshooting Decision Tree

```mermaid
graph TD
    A[CI Failed] --> B{Много jobs упало сразу?}
    B -->|Да| C[Проверить dependency-preflight]
    B -->|Нет| D{Какой check failed?}
    
    D -->|checks-complete| E[Открыть lint logs]
    E --> F{lint OK?}
    F -->|Нет| G[Исправить lint errors]
    F -->|Да| H[Открыть c901-governance]
    H --> I{c901 OK?}
    I -->|Нет| J[Снизить complexity]
    I -->|Да| K[Открыть arch-tests]
    
    D -->|coverage-verify| L[Скачать coverage-report artifact]
    L --> M[Найти непокрытый код]
    M --> N[Добавить тесты]
    
    D -->|type-check| O[Локально: mypy --strict]
    O --> P[Исправить type errors]
    
    D -->|schema-governance-status| Q[Проверить contract exports]
    Q --> R[Обновить schemas]
    
    D -->|detect-secrets| S[Найти leaked secret]
    S --> T[Rotate secret + commit fix]
    
    C --> U[uv lock --upgrade локально]
    G --> V[git commit + push]
    J --> V
    N --> V
    P --> V
    R --> V
    T --> V
    U --> V
    V --> W[CI перезапустится]
```

## Git Worktree Usage Pattern

```mermaid
graph LR
    A[Main worktree] --> B{Сложная задача?}
    B -->|Нет| C[Обычная feature branch]
    B -->|Да| D[Governed worktree helper]
    D --> E[Isolated worktree]
    E --> F[Разработка]
    F --> G[Commit + push]
    G --> H[PR создан]
    H --> I[cd назад в main]
    I --> J[git worktree remove]
    J --> K[Cleanup]
```

---

**Примечание:** Все диаграммы используют Mermaid синтаксис и совместимы с GitHub, MkDocs, и другими markdown рендерерами с поддержкой Mermaid.

