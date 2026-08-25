# Iteration 3 — gates rollup

```text
python -m scripts.engineering.qa report-debt-governance-gates --update
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
```

Live `--check` 0 fail (45/45). `generated_artifact_drift` count 1→0. No scorecard yaml budget change.
