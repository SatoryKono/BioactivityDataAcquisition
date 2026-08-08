# Devin Error Recovery Guide

## Common Error Scenarios and Recovery Procedures

### py-test-bot fails

**Symptoms:**
- Test failures in `reports/pytest/`
- FAIL-XXX references in test output
- Coverage reports show failures

**Recovery Steps:**
1. Check test output: `cat reports/pytest/latest.log`
2. Identify specific FAIL-XXX reference from the failure
3. Run py-debug-bot with the FAIL reference:
   ```python
   run_subagent(
       title="debug FAIL-XXX",
       task="Follow .devin/agents/py-debug-bot/AGENT.md for FAIL-XXX",
       profile="py-debug-bot",
       is_background=False
   )
   ```
4. Apply the fix suggested by py-debug-bot
5. Re-run py-test-bot to verify the fix
6. If still failing, repeat steps 3-5 (max 5 iterations)

**Quick Fix:**
```bash
make devin-fix-bug
```

### py-audit-bot reports MUST findings

**Symptoms:**
- MUST findings in `review_py-audit-bot_*.md`
- Blocker issues that prevent task completion
- Critical governance violations

**Recovery Steps:**
1. Review the audit findings: `cat reports/*/review_py-audit-bot_*.md`
2. Address findings in priority order:
   - MUST: Critical blockers (must fix)
   - SHOULD: Important issues (should fix if possible)
   - MAY: Nice-to-have improvements (optional)
3. For each MUST finding:
   - Identify the root cause
   - Apply the appropriate fix
   - Verify the fix addresses the finding
4. Re-run py-audit-bot for verification:
   ```python
   run_subagent(
       title="re-audit",
       task="Follow .devin/agents/py-audit-bot/AGENT.md for re-audit",
       profile="py-audit-bot",
       is_background=False
   )
   ```
5. Continue until no MUST findings remain

**Quick Reference:**
- See `.devin/QUICK_REFERENCE.md` for profile selection
- Use `make devin-audit-config` for config-related audits

### Permission denied errors

**Symptoms:**
- "Permission denied" errors when trying to read/write files
- Devin asks for permission but request is denied
- File access blocked by security policies

**Recovery Steps:**
1. Check current permissions in `.devin/config.json`
2. Use smart permission mode for development:
   ```bash
   make devin DEVIN_ARGS='--permission-mode smart'
   ```
3. Grant specific permissions as needed during the session
4. If persistent permission issues, consider:
   - Using development permission profile (if available)
   - Adjusting `.devin/config.json` permissions
   - Contacting repository administrator for policy review

**Note:** `.env` files always require explicit approval per repository guardrails.

### MCP server not available

**Symptoms:**
- "MCP server not available" errors
- Connection refused to MCP endpoints
- MCP-related functionality fails

**Recovery Steps:**
1. Check MCP server status:
   ```bash
   make devin-mcp-start
   ```
2. If MCP servers not running, start appropriate tier:
   ```bash
   # For simple tasks
   make devin-mcp-start-minimal
   
   # For standard development
   make devin-mcp-start-standard
   
   # For full functionality
   make devin-mcp-start-full
   ```
3. Check MCP health:
   ```bash
   PYTHONDONTWRITEBYTECODE=1 bash scripts/ops/runtime/mcp/health-shared.sh daily
   ```
4. If specific server fails, restart that server manually
5. Re-run the task that failed

**Quick Fix:**
```bash
make devin-mcp-start-minimal
```

### Memory workflow fails

**Symptoms:**
- Memory workflow errors during pre/post-task operations
- Memory retrieval or storage failures
- Session note creation failures

**Recovery Steps:**
1. Check memory status:
   ```bash
   python -m memory.tooling.workflow status
   ```
2. Re-run pre-task if it failed:
   ```bash
   python -m memory.tooling.workflow pre-task --task-id <id> --title "<task>"
   ```
3. Continue with the main task
4. Re-run post-task after task completion:
   ```bash
   python -m memory.tooling.workflow post-task --task-id <id> --title "<task>" --summary "<result>"
   ```
5. If memory system is down, consider:
   - Running task without memory workflow (for simple tasks)
   - Restarting memory services
   - Checking Neo4j connection if using graph memory

**Note:** Memory workflow is optional for simple tasks but recommended for complex work.

### py-config-bot gap analysis critical findings

**Symptoms:**
- py-config-bot reports critical gap analysis findings
- Configuration validation failures
- Schema mismatches in configs

**Recovery Steps:**
1. Review gap analysis output from py-config-bot
2. Address critical findings:
   - Schema mismatches: Update config to match schema
   - Missing required fields: Add required fields
   - Invalid values: Correct to valid values
3. Re-run py-config-bot for verification:
   ```python
   run_subagent(
       title="config verification",
       task="Follow .devin/agents/py-config-bot/AGENT.md for verification",
       profile="py-config-bot",
       is_background=False
   )
   ```
4. Ensure gap analysis shows 0 critical findings before proceeding

**Quick Fix:**
```bash
make devin-audit-config
```

### py-doc-bot documentation validation failures

**Symptoms:**
- Documentation validation errors
- Link checking failures
- Style guide violations

**Recovery Steps:**
1. Review py-doc-bot output for specific validation failures
2. Fix documentation issues:
   - Broken links: Update or remove
   - Style violations: Follow project style guide
   - Missing sections: Add required documentation
3. Re-run py-doc-bot for verification
4. Use targeted py-audit-bot for docs audit if needed

**Quick Fix:**
```bash
make devin-update-docs
```

### Profile selection confusion

**Symptoms:**
- Uncertainty about which profile to use for a task
- Wrong profile selected leading to inefficiencies
- Workflow not matching task requirements

**Recovery Steps:**
1. Use interactive profile selector:
   ```bash
   make devin-select-profile
   ```
2. Follow the guide to select appropriate profile
3. Refer to `.devin/QUICK_REFERENCE.md` for detailed profile information
4. If still uncertain, use ORCHESTRATION.md for guidance

**Profile Selection Quick Reference:**
- Bug fix → py-debug-bot
- Feature → py-plan-bot → orchestrator
- Config → py-config-bot
- Documentation → py-doc-bot
- Testing → py-test-bot
- Audit → py-audit-bot

### Workflow timeout or hanging

**Symptoms:**
- Workflow hangs indefinitely
- No progress for extended period
- Timeout errors

**Recovery Steps:**
1. Check if task is actually running (may be slow but not hung)
2. If truly hung, terminate the current session
3. Restart with simplified workflow if possible:
   - Use quick-fix workflow instead of full workflow
   - Use minimal MCP plane instead of full
   - Break task into smaller chunks
4. Consider using background mode for long-running operations:
   ```python
   run_subagent(
       title="long-running task",
       task="...",
       profile="py-test-bot",
       is_background=True
   )
   ```

### Git conflicts during workflow

**Symptoms:**
- Git merge conflicts
- Unable to commit changes
- Branch synchronization issues

**Recovery Steps:**
1. Check git status: `git status`
2. Resolve conflicts using standard git procedures
3. Use `git mergetool` if available
4. Test resolution before committing
5. Re-run workflow from the point of failure

**Quick Fix:**
```bash
git status
git add .
git commit -m "resolve conflicts"
```

## General Troubleshooting Tips

### Before Escalating
1. Check `.devin/QUICK_REFERENCE.md` for quick solutions
2. Review relevant workflow documentation in `.devin/workflows/`
3. Check if similar issue is documented in this guide
4. Try simplified workflow if available

### When to Escalate
- Error persists after 3 recovery attempts
- Error involves system-level issues (MCP, memory, infrastructure)
- Error requires policy or governance changes
- Error is blocking critical work and no workaround available

### Documentation Resources
- `.devin/QUICK_REFERENCE.md` - Quick reference for common tasks
- `.devin/agents/DEVIN-SETUP-GUIDE.md` - Setup and configuration
- `.devin/agents/ORCHESTRATION.md` - Workflow orchestration
- `.devin/agents/DEVIN-RUNTIME.md` - Runtime mapping
- `.devin/workflows/*.md` - Specific workflow documentation

### Getting Help
```bash
# Show all available commands
make help

# Check Devin status
make devin-check

# List workflows
make devin-workflows

# Select profile interactively
make devin-select-profile
```

## Prevention Tips

1. **Use appropriate workflows** - Don't use full workflow for simple tasks
2. **Start with minimal MCP plane** - Scale up as needed
3. **Follow profile selection guide** - Use right tool for the job
4. **Check permissions early** - Resolve permission issues before main work
5. **Use memory workflow** - For complex tasks, maintain good memory practices
6. **Test incrementally** - Don't wait until end to validate
7. **Document decisions** - Keep track of why certain approaches were taken

## Performance Optimization

1. **Use background mode** for long-running operations
2. **Use tiered MCP startup** - Minimal for simple tasks
3. **Use quick-fix shortcuts** - For routine bug fixes
4. **Parallelize when possible** - Independent subagents can run in parallel
5. **Cache results** - Avoid redundant computations
