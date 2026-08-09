# Platform tooling and MCP wrapper generation

Status: published guide. Owner: platform/setup scripts. Retirement criterion:
merge into the general developer setup guide when all legacy per-platform MCP
wrapper implementations have been retired.

## Platform abstraction

Repository setup code should use
`scripts.engineering.common.platform.detect_platform()` instead of adding new
independent `os.name`, `sys.platform`, or WSL environment branches. The result
distinguishes native Windows, WSL, Linux, macOS, and other POSIX hosts and owns
the shell/suffix/permission decisions shared by setup tooling.

Shell and PowerShell entrypoints remain valid compatibility surfaces. New
cross-platform behavior belongs in Python; thin platform launchers may delegate
to it when an operating system still requires a native entrypoint.

## Catalog-driven MCP wrappers

`scripts/ops/runtime/mcp/shared-servers.json` owns the shared server name and
wrapper stem. `scripts.ai.codex.setup_mcp` reads that mapping directly; it does
not maintain another 19-server wrapper table.

Validate both platform implementations:

```bash
python -m scripts.ai.mcp wrappers check
```

List the resolved mapping or dispatch one server through its native wrapper:

```bash
python -m scripts.ai.mcp wrappers list
python -m scripts.ai.mcp wrappers run context7
```

Generate deterministic compatibility shims for a local client or packaging
step without adding tracked hand-written pairs:

```bash
python -m scripts.ai.mcp wrappers generate --output /tmp/bioetl-mcp-wrappers
```

Generated shims delegate back to the repository dispatcher. The existing
server-specific `.sh` and `.ps1` files remain compatibility implementations
during the migration; their catalog pairing is enforced in CI. A new shared
server must add one catalog entry and both implementation variants until that
server has a platform-neutral Python backend.

