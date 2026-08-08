# Devin Interactive Tutorial

## Welcome to Devin CLI for BioETL

This tutorial will guide you through the basic workflow of using Devin CLI with BioETL custom subagent profiles.

## Prerequisites

- Devin CLI v3000.3 or newer installed
- Repository cloned and accessible
- Basic familiarity with BioETL project structure

## Tutorial Steps

### Step 1: Verify Devin Setup

First, let's verify that Devin is properly configured:

```bash
make devin-check
```

This will check:
- Devin CLI installation
- Configuration files validity
- MCP server status
- Skills availability

**Expected output:** All checks should pass with ✓ symbols.

### Step 2: Start Devin CLI

Launch the Devin CLI with BioETL runtime configuration:

```bash
make devin
```

This will:
- Refresh MCP configuration
- Start Devin from repository root
- Load AGENTS.md and .devin/** configuration

### Step 3: Explore Available Profiles

Devin provides 9 custom subagent profiles. Let's explore them:

**Option A:** Use interactive profile selector
```bash
make devin-select-profile
```

**Option B:** Manual exploration
- Bug fix → py-debug-bot
- Feature → py-plan-bot → orchestrator
- Config → py-config-bot
- Documentation → py-doc-bot
- Testing → py-test-bot
- Audit → py-audit-bot

### Step 4: Try a Simple Task

Let's practice with a simple documentation update:

```bash
make devin-update-docs
```

This will:
- Run py-doc-bot for documentation updates
- Run py-audit-bot for targeted docs audit
- Use simplified 2-step workflow (vs 8-step full workflow)

### Step 5: Explore Quick Reference

Check the comprehensive quick reference guide:

```bash
cat .devin/QUICK_REFERENCE.md
```

This includes:
- Common task shortcuts
- Profile selection guide
- Workflow templates
- Error recovery procedures
- Performance tips

### Step 6: Explore Available Workflows

List all available workflows:

```bash
make devin-workflows
```

Available workflows:
- audit-documents
- deepwiki-regeneration
- master
- post-change
- pre-commit
- qodo-sync
- review
- shared-validation

### Step 7: Try Tiered MCP Startup

Experience different MCP startup profiles:

```bash
# Minimal MCP plane (fastest)
make devin-mcp-start-minimal

# Standard MCP plane (balanced)
make devin-mcp-start-standard

# Full MCP plane (all features)
make devin-mcp-start-full
```

### Step 8: Practice with Quick-Fix Workflow

For a simple bug fix, try the quick-fix workflow:

```bash
make devin-fix-bug
```

This uses a 5-step workflow vs the full 8-step workflow (~60% faster).

## Common Patterns

### Pattern 1: Bug Fix
```bash
make devin-fix-bug
```

### Pattern 2: Feature Addition
```bash
make devin-add-feature
```

### Pattern 3: Documentation Update
```bash
make devin-update-docs
```

### Pattern 4: Config Audit
```bash
make devin-audit-config
```

## Next Steps

1. **Explore ORCHESTRATION.md** for detailed workflow information
2. **Try different profiles** for various task types
3. **Use simplified workflows** for routine tasks
4. **Reference troubleshooting guide** when encountering errors
5. **Use memory workflow** for complex tasks

## Getting Help

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

## Tips for Success

1. **Start simple** - Use quick-fix workflows for routine tasks
2. **Use appropriate MCP tier** - Minimal for simple tasks, full for complex
3. **Follow profile selection guide** - Use right tool for the job
4. **Reference quick guide** - Check .devin/QUICK_REFERENCE.md often
5. **Use error recovery guide** - .devin/troubleshooting.md for common issues

## Tutorial Complete!

You now have a basic understanding of:
- Devin CLI setup and verification
- Available subagent profiles
- Quick-fix shortcuts
- Workflow discovery
- Tiered MCP startup
- Error recovery resources

For more detailed information, refer to:
- `.devin/agents/DEVIN-SETUP-GUIDE.md` - Setup and configuration
- `.devin/agents/ORCHESTRATION.md` - Detailed workflow orchestration
- `.devin/QUICK_REFERENCE.md` - Comprehensive quick reference
- `.devin/troubleshooting.md` - Error recovery procedures
