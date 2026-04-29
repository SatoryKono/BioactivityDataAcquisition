## 2024-05-19 - py-test-swarm L1 orchestrator execution
**Learning:** Generating robust test telemetry and orchestrator L1 reports from realistic test structures requires proper fetching of test nodes via `pytest --collect-only` and dynamically applying them.
**Action:** When performing swarm reporting, write a custom Python script that collects actual local nodes and maps them to JSONL schemas as defined in orchestration prompts, then uses `git add -f` for directories that are strictly in `.gitignore`.
