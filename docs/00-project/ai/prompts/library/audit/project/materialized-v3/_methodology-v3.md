2. МЕТОДОЛОГИЯ АНАЛИЗА
2.1. Scope и единица оценки
Единица оценки — полный operator prompt после materialization его общих includes и параметров. Оценивается текстовый контракт: предметная методика, guardrails, доказательность, повторяемость и outputs. Исполнение промптов не проводилось; runtime quality проекта не выводится из оценки prompt text.
Baseline репозитория: main @ 3aba8559a58038cd9ff9a90621f19ea39b930a2f. Для первых 10 объектов сохранены score vectors предыдущего аудита; для 14 new2 — оценки объединённого отчёта. Улучшенные compositions оцениваются как экспертная projection после устранения зафиксированных process gaps.
2.2. Категории оценки и веса

Все веса равны 10%. Это сохраняет прямую сопоставимость с предыдущим отчётом и не позволяет одному эффектному, но узкому guardrail скрыть слабость предметной методики или lifecycle.
2.3. Формула и шкала
WeightedScore = Σ(C_i × W_i), i=1..10
W_i = 0.10
Delta = ImprovedWeightedScore - BaselineWeightedScore


2.4. Evidence hierarchy
1. FACT: path+symbol/line либо command+scope+timestamp+exit+relevant output.
2. CONTRADICTION: два канонических surface дают несовместимые правила.
3. INFERENCE: вывод из FACT, помеченный как inference и не используемый для mutation без проверки.
4. GAP/NOT_PROVEN: данных недостаточно; Issue и mutation запрещены.
2.5. Ключевой архитектурный долг промптов

2.6. Почему Kernel v3.0 является архитектурным решением
Kernel владеет orchestration state machine, permissions, evidence contract, ledger, Issue sync, outputs и stop semantics.
Domain overlay владеет только OBJECT/SCOPE/SSOT/contours/evidence/validation/domain stops/extras.
Execution profile владеет конкретными значениями MODE и ALLOW_*; он не изменяет source card или kernel defaults.
Compiler materializes kernel + overlay + profile и вычисляет prompt_sha8, делая каждый запуск идентифицируемым.
Schemas и golden tests превращают prompt library из набора prose files в проверяемую конфигурационную систему.