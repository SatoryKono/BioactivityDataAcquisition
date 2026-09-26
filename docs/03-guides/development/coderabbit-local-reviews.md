# Local CodeRabbit review launcher

Use `scripts/ops/run-coderabbit-reviews.sh changes` for one local diff review.
CodeRabbit CLI 0.7.5 reviews Git changes; a successful run does not establish
coverage of unchanged project files. PR reviews use the CodeRabbit GitHub App
and `.coderabbit.yaml` separately.

## Windows / WSL

Run from PowerShell, with the repository visible in Ubuntu. Resolve the checkout
with `wslpath` instead of a machine-specific mount path:

```powershell
# Convert the current Windows checkout to the distro path (no hardcoded drive).
$repoWsl = (wsl -d Ubuntu wslpath -a (Get-Location).Path).Trim()

# Validate credentials, backend/WebSocket connectivity, and configuration.
wsl -d Ubuntu --cd $repoWsl --exec bash scripts/ops/run-coderabbit-reviews.sh --preflight

# Review staged and unstaged tracked changes once.
wsl -d Ubuntu --cd $repoWsl --exec bash scripts/ops/run-coderabbit-reviews.sh changes --uncommitted

# Review changes against an explicit baseline within one directory.
wsl -d Ubuntu --cd $repoWsl --exec bash scripts/ops/run-coderabbit-reviews.sh changes --base origin/main --dir src/bioetl/interfaces
```

The same Bash commands work directly in Linux. CodeRabbit must be on `PATH`.
The launcher changes to the repository root before invoking the CLI.

## Credentials

The launcher reads only `CODERABBIT_API_KEY` from the root `.env` using
`python-dotenv` with interpolation disabled. It never sources or changes the
file. A non-empty root key takes precedence over the process environment;
otherwise an existing process key or cached CodeRabbit login is used.
Do not enable shell tracing for a credential-bearing invocation.

The parser uses `${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python`, falling
back to `python3`. Set `BIOETL_CODERABBIT_PYTHON` to an executable Python with
`python-dotenv` installed when needed. Standard `python3` is also required for
NDJSON result validation. Missing parser dependencies fail the preflight.
Root `.env` changes require explicit per-task approval.

## Evidence and failure handling

Default output: `reports/quality/coderabbit/local/`; override with `--log-dir`.
The launcher saves doctor/config logs and a unique review NDJSON stream, stderr,
HEAD, initial Git status, and baseline diff. The snapshot describes the working
tree before submission; concurrent edits can invalidate source correspondence.
New untracked files are excluded. Stop concurrent editing or use an isolated
checkout when an immutable audit snapshot is required.

Every review receives `AGENTS.md` and `.coderabbit.yaml` through `-c` and uses
`--agent` output. Authentication, connectivity, schema, or CLI failures exit
non-zero. An error event, a skipped scope, or missing completion also fails;
these outcomes must not be reported as zero issues. Findings require separate
triage; this launcher does not apply suggested fixes or publish issues.

`--preflight` stops before review submission. On `WebSocket closed`, inspect
`doctor.log` and check access to `https://app.coderabbit.ai` and
`wss://ide.coderabbit.ai/ws`. Successful authentication alone does not prove
review-service connectivity. Configuration validation additionally needs
`https://www.coderabbit.ai/integrations/schema.v2.json`.

## Legacy topics and CI

Explicit topics `architecture-boundaries`, `adapters-resilience`,
`pipelines-determinism`, `security`, and `contracts-docs-drift` retain their
additional local quality commands. `--coderabbit-only` skips those commands.
The legacy default `all` runs five reviews of the same selected diff; it is not
a full-project partition. Prefer explicit `changes` and one real `--dir` scope
per run. Count scope files and split reviews within the server's limit.

The legacy comprehensive launcher and historical playbook examples still need
migration from `--plain` and historical scope assumptions. Use the commands
above for CLI 0.7.5.

`.github/workflows/coderabbit.yml` is separately classified `keep-disabled` in
the repository CI map. Its tracked definition targets trusted push/manual
events and skips review when its API secret is absent. Local setup does not
enable the workflow or make it a merge gate. Do not raise debt budgets to
silence review issues.
