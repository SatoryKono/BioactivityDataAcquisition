# DeepWiki Regeneration Workflow

## Purpose

This workflow defines the process for regenerating and updating the local `.devin/wiki-*.json` files to reflect the current state of the repository. DeepWiki is a derived navigation layer and must always align with canonical sources (docs, configs, code, tests, ADRs).

## Trigger Conditions

Regenerate DeepWiki when:
- Significant changes to architecture (composition, application core, domain layer)
- Major updates to AI runtime (skills, workflows, MCP configuration)
- Governance artifact updates (debt scorecard, quality gates)
- New ADRs or documentation restructuring
- Removal of deprecated scripts or tools
- GitHub issue requesting DeepWiki regeneration (e.g., #8035)

## Pre-Update Checklist

- [ ] Current wiki files backed up in git
- [ ] No uncommitted changes in canonical sources
- [ ] DeepWiki credentials validated (DEEPWIKI_API_KEY, DEEPWIKI_ORGANISATION_ID)
- [ ] MCP DeepWiki server accessible
- [ ] Identified affected modules based on changed canonical anchors

## Update Process

### Phase 1: Preparation

1. **Backup current wiki files**
   ```bash
   git add .devin/wiki-*.json
   git commit -m "backup: wiki files before DeepWiki regeneration - issue #<number>"
   ```

2. **Audit canonical sources**
   - Check changes in `docs/00-project/` (last 30 days)
   - Check changes in `docs/02-architecture/decisions/`
   - Check changes in `AGENTS.md`
   - Check changes in `.devin/agents/` and `.devin/skills/`

3. **Identify outdated sections**
   - Compare wiki content with current canonical sources
   - Find deleted/renamed files
   - Check ADR citation accuracy

### Phase 2: Targeted Updates via DeepWiki MCP

Use `mcp_call_tool` with `deepwiki` server for targeted updates:

**Core modules:**
```python
mcp_call_tool(
    server_name="deepwiki",
    tool_name="ask_question",
    arguments={
        "repoName": "SatoryKono/BioactivityDataAcquisition",
        "question": "Update the AI Runtime Governance section to reflect current Devin skills, workflows, and MCP configuration..."
    }
)
```

**Architecture module:**
```python
mcp_call_tool(
    server_name="deepwiki",
    tool_name="ask_question",
    arguments={
        "repoName": "SatoryKono/BioactivityDataAcquisition",
        "question": "Update architecture documentation to reflect recent changes in composition layer, application core, and quality ports..."
    }
)
```

**Observability module:**
```python
mcp_call_tool(
    server_name="deepwiki",
    tool_name="ask_question",
    arguments={
        "repoName": "SatoryKono/BioactivityDataAcquisition",
        "question": "Update observability documentation to reflect current Grafana dashboards, metrics catalog, and monitoring infrastructure..."
    }
)
```

**Reference module:**
```python
mcp_call_tool(
    server_name="deepwiki",
    tool_name="ask_question",
    arguments={
        "repoName": "SatoryKono/BioactivityDataAcquisition",
        "question": "Update API reference documentation to reflect current CLI commands, interfaces, and public APIs..."
    }
)
```

### Phase 3: Manual Updates

Apply DeepWiki responses to local wiki files:
- `.devin/wiki-core.json` - AI Runtime Governance, Memory Workflow, MCP Surfaces
- `.devin/wiki-architecture.json` - Architecture layers, ADR updates
- `.devin/wiki-observability.json` - Dashboards, metrics, alerting, observability skills
- `.devin/wiki-reference.json` - CLI commands, configuration, operational procedures

### Phase 4: Validation

1. **Validate against canonical sources**
   - Check that all file references exist
   - Verify ADR citations are accurate
   - Ensure no contradictions with canonical sources

2. **Remove outdated references**
   - Delete references to deleted scripts (e.g., CodeRabbit scripts)
   - Update references to reorganized scripts
   - Fix broken file paths

3. **Validate JSON structure**
   - Ensure all JSON files are valid
   - Check `wiki-index.json` module list
   - Verify parent-child relationships

### Phase 5: Testing

1. **Test with memory RAG**
   - Verify `src/memory/rag/devin_wiki.py` can process updated files
   - Check that `build_devin_wiki_records()` succeeds

2. **Test with Devin MCP**
   - Verify DeepWiki MCP server can use updated wiki
   - Test `read_wiki_structure` and `read_wiki_contents`

## Validation Checklist

- [ ] No contradictions with canonical sources (docs, configs, code, tests, ADRs)
- [ ] All file references exist and are accurate
- [ ] JSON structure is valid for all wiki files
- [ ] Memory RAG processes successfully
- [ ] Devin MCP can use updated wiki
- [ ] DeepWiki MCP returns correct structure
- [ ] No references to deleted files (CodeRabbit scripts, old tests)
- [ ] ADR citations are current and accurate
- [ ] Skills and workflows lists are up-to-date

## Post-Update Actions

1. **Commit changes**
   ```bash
   git add .devin/wiki-*.json
   git commit -m "docs(deepwiki): regenerate wiki files - issue #<number>

   - Update AI Runtime Governance with current skills/workflows
   - Reflect architecture changes (composition, application core, domain)
   - Update observability documentation (dashboards, metrics, skills)
   - Update reference documentation (CLI, scripts reorganization)
   - Remove references to deleted CodeRabbit scripts
   - Add recent ADR updates (ADR-040, ADR-034, ADR-037, ADR-050)

   Generated with [Devin](https://devin.ai)"
   ```

2. **Close GitHub issue**
   - Update issue with summary of changes
   - List updated modules
   - Note any skipped validations with reasons
   - Confirm DeepWiki MCP functionality

## Critical Rules

1. **DeepWiki is derived only**: Never contradict canonical sources
2. **Canonical sources priority**: docs/, configs/, src/, tests/, ADRs
3. **Validation mandatory**: Every update must be checked
4. **No automatic commits**: All changes require manual review
5. **Preserve modular structure**: Don't change wiki-index.json without necessity
6. **Technical debt guardrail**: Never increase technical debt budgets

## Related Documentation

- `AGENTS.md` - Root operating contract for AI runtime
- `docs/00-project/ai/memory/README.md` - Memory subsystem documentation
- `docs/00-project/ai/memory/agent-memory.md` - Agent memory guidance
- `src/memory/rag/devin_wiki.py` - Wiki RAG processing
- `.devin/mcp_config.json` - MCP server configuration

## Automation

For future automation, see:
- `scripts/ai/update_deepwiki.py` - Automated update script (to be created)
- `Makefile` targets: `deepwiki-backup`, `deepwiki-update`, `deepwiki-validate`
