# Optional Agent Tools

BioETL exposes AgentDebugX and ProofAgent only through a subprocess boundary.
They are optional diagnostics: absence or failure never changes the result of a
core BioETL test, Proof-or-Stop gate, or lifecycle transition.

## Install

The default environment remains unchanged. Install one or both tools explicitly:

```bash
bash scripts/engineering/dev/setup_env_wsl.sh --agent-tools agentdebugx
bash scripts/engineering/dev/setup_env_wsl.sh --agent-tools proofagent
bash scripts/engineering/dev/setup_env_wsl.sh --agent-tools all
```

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1 -AgentTools agentdebugx
.\scripts\engineering\dev\setup_env_windows.ps1 -AgentTools proofagent
.\scripts\engineering\dev\setup_env_windows.ps1 -AgentTools all
```

The lock-backed extras pin `agentdebugx==0.3.1` and
`proofagent-harness==0.11.0`. When `all` is selected, each optional tool is
attempted separately so one installation failure does not prevent the other.

## Use

```bash
python -m scripts.ai.agent_tools doctor
python -m scripts.ai.agent_tools debug \
  --task-id issue-8408 \
  --trajectory tests/fixtures/agent-tools/agentdebugx-failure.json
python -m scripts.ai.agent_tools evaluate \
  --task-id issue-8412 \
  --events tests/fixtures/agent-tools/proofagent-clean.jsonl
```

For a bounded current-diff screen, pass both `--from-git` and an explicit
`--scope`. ProofAgent is always invoked with `--assess never --no-upload`.
AgentDebugX is always invoked with `--mode deterministic`.

Stable exit codes are `0` (completed), `2` (invalid input), `3` (unavailable),
`4` (wrong version), `5` (timeout), `6` (vendor/source-binding failure), and
`7` (malformed vendor output). ProofAgent's own `NOT_READY` exit code is
normalized into an advisory `FAIL` verdict, not a BioETL process failure.

Inputs are restricted to `tests/fixtures/agent-tools/` and
`reports/ai/agent-tools/inputs/`. Results are written only below
`reports/ai/agent-tools/<tool>/<task-id>/`. Captured output is redacted and
stored with user-only permissions. Secret-bearing environment variables are not
forwarded to either subprocess.

## Uninstall and rollback

Re-run the platform setup command without `--agent-tools` / `-AgentTools`; the
lock-backed `uv sync` removes optional packages. For a pip-managed fallback:

```bash
python -m pip uninstall agentdebugx proofagent-harness
```

Removing these packages requires no code or configuration rollback because the
adapters detect `UNAVAILABLE` and core BioETL execution does not import them.

