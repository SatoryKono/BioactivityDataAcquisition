# Итерация 1 — inventory и merge gates

`surface_score: 1/3`.

Live GitHub API опроверг policy SSOT: branch protection отсутствует, оба ruleset disabled, а последний `Tests` run датирован 2026-07-17. Finding `TEST-SYS-001` доказан; #8619 переоткрыт вместо создания дубликата.

Команды: `gh api .../branches/main/protection/required_status_checks`, `gh api .../rulesets`, `gh run list --workflow tests.yml`.
