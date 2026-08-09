# Devin CLI Optimization: Permission Profiles and Smart MCP Management

## Problem
Current Devin configuration has inflexibility issues:
- Conservative permissions slow down workflow for routine development tasks
- All 18 MCP servers always start even when not needed (~2 minutes startup)
- No permission profiles for different development contexts
- No lazy loading for rarely used MCP servers
- One-size-fits-all configuration doesn't match different use cases

This creates unnecessary friction and reduces efficiency for different development scenarios.

## Proposed Solution
Implement configuration optimization to improve flexibility and reduce startup time:

### 1. Permission Profiles
Add permission profiles to `.devin/config.json` for different development contexts:

```json
{
  "version": 2,
  "permission_profiles": {
    "strict": {
      "ask": ["Read(**/.env*)", "Write(**/.env*)"],
      "allow": [
        "Read(**/.devin/**)",
        "Read(**/docs/**)",
        "Read(**/configs/**)",
        "Read(**/src/**)",
        "Read(**/tests/**)",
        "Read(**/scripts/**)",
        "Read(**/Makefile)",
        "Exec(make)",
        "Exec(git)",
        "Exec(python)",
        "Exec(pytest)",
        "Exec(mypy)",
        "Exec(ruff)"
      ],
      "deny": ["Write(**/.env*)", "Write(**/docs/**)", "Write(**/configs/**)"]
    },
    "development": {
      "ask": ["Read(**/.env*)", "Write(**/.env*)"],
      "allow": [
        "Read(**/.devin/**)",
        "Read(**/docs/**)",
        "Write(**/docs/**)",
        "Read(**/configs/**)",
        "Write(**/configs/**)",
        "Read(**/src/**)",
        "Write(**/src/**)",
        "Read(**/tests/**)",
        "Write(**/tests/**)",
        "Read(**/scripts/**)",
        "Read(**/Makefile)",
        "Exec(make)",
        "Exec(git)",
        "Exec(python)",
        "Exec(pytest)",
        "Exec(mypy)",
        "Exec(ruff)"
      ],
      "deny": ["Write(**/.env*)"]
    }
  },
  "permissions": {
    "ask": ["Read(**/.env*)", "Write(**/.env*)"],
    "allow": [
      "Read(**/.devin/**)",
      "Read(**/docs/**)",
      "Read(**/configs/**)",
      "Read(**/src/**)",
      "Read(**/tests/**)",
      "Read(**/scripts/**)",
      "Read(**/Makefile)",
      "Exec(make)",
      "Exec(git)",
      "Exec(python)",
      "Exec(pytest)",
      "Exec(mypy)",
      "Exec(ruff)"
    ],
    "deny": ["Write(**/.env*)", "Write(**/docs/**)", "Write(**/configs/**)"]
  },
  "read_config_from": {
    "agents_standard": true
  }
}
```

Add profile selection to Makefile:

```makefile
.PHONY: devin-strict devin-dev

devin-strict:
	@echo "Using strict permission profile"
	@$(DEVIN) $(DEVIN_ARGS) --permission-profile strict

devin-dev:
	@echo "Using development permission profile"
	@$(DEVIN) $(DEVIN_ARGS) --permission-profile development
```

**Expected impact:** 40% less permission friction for development tasks

### 2. Smart MCP Server Management
Add lazy loading and tiered configuration to `.devin/mcp_config.json`:

```json
{
  "mcpServers": {
    "memory": {
      "url": "http://127.0.0.1:8826/mcp",
      "autostart": true,
      "essential": true,
      "description": "Memory storage and retrieval"
    },
    "filesystem": {
      "url": "http://127.0.0.1:8827/mcp",
      "autostart": true,
      "essential": true,
      "description": "File system operations"
    },
    "fetch": {
      "url": "http://127.0.0.1:8821/mcp",
      "autostart": true,
      "essential": true,
      "description": "HTTP fetching"
    },
    "github": {
      "url": "http://127.0.0.1:8820/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "GitHub operations"
    },
    "docker": {
      "url": "http://127.0.0.1:8817/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Docker operations"
    },
    "prometheus": {
      "url": "http://127.0.0.1:8822/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Prometheus queries"
    },
    "grafana": {
      "url": "http://127.0.0.1:8823/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Grafana operations"
    },
    "brave-search": {
      "url": "http://127.0.0.1:8811/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Web search"
    },
    "neo4j-cypher": {
      "url": "http://127.0.0.1:8824/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Neo4j Cypher queries"
    },
    "neo4j-memory": {
      "url": "http://127.0.0.1:8825/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Neo4j memory operations"
    },
    "mermaid": {
      "url": "http://127.0.0.1:8818/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Mermaid diagram operations"
    },
    "context7": {
      "url": "http://127.0.0.1:8815/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Context7 operations"
    },
    "ast-grep": {
      "url": "http://127.0.0.1:8816/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "AST grep operations"
    },
    "mcp-code-interpreter": {
      "url": "http://127.0.0.1:8829/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Code interpreter"
    },
    "deja": {
      "url": "http://127.0.0.1:8814/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Deja operations"
    },
    "adr-analysis": {
      "url": "http://127.0.0.1:8813/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "ADR analysis"
    },
    "mutmut": {
      "url": "http://127.0.0.1:8830/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Mutation testing"
    },
    "code-analyzer": {
      "url": "http://127.0.0.1:8828/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "Code analysis"
    },
    "github-actions": {
      "url": "http://127.0.0.1:8831/mcp",
      "autostart": false,
      "on_demand": true,
      "description": "GitHub Actions operations"
    },
    "deepwiki": {
      "url": "https://mcp.deepwiki.com/mcp",
      "autostart": false,
      "on_demand": true,
      "headers": {
        "x-deepwiki-api-key": "${env:DEEPWIKI_API_KEY}",
        "x-deepwiki-organisation-id": "${env:DEEPWIKI_ORGANISATION_ID}"
      },
      "description": "DeepWiki operations"
    },
    "ref": {
      "url": "https://api.ref.tools/mcp",
      "autostart": false,
      "on_demand": true,
      "headers": {
        "x-ref-api-key": "${env:REF_TOOL_API_KEY}"
      },
      "description": "Ref tools operations"
    }
  }
}
```

**Expected impact:** 75% faster MCP startup for simple tasks (2 → 0.5 minutes)

### 3. Profile-Specific MCP Configuration
Create profile-specific MCP configurations in `.devin/agents/<profile>/config.json`:

Example for py-debug-bot:
```json
{
  "permissions": {
    "allow": ["Read(**/src/**)", "Write(**/src/**)", "Read(**/tests/**)", "Write(**/tests/**)", "Exec(python)", "Exec(pytest)"],
    "deny": ["Write(**/configs/**)", "Write(**/docs/**)"]
  },
  "mcp_servers": ["memory", "filesystem", "fetch"],
  "tools": ["read", "write", "edit", "exec", "grep", "find_file_by_name"]
}
```

**Expected impact:** 30% faster profile-specific tasks

## Scope
Infrastructure / DevOps

## Alternatives considered
1. **Dynamic permission system** - More complex, harder to maintain
2. **MCP server pooling** - Requires significant infrastructure changes
3. **Containerized MCP servers** - Outside current scope, significant DevOps overhead

## Implementation plan
- [ ] Add permission profiles to .devin/config.json
- [ ] Add permission profile selection to Makefile
- [ ] Add lazy loading configuration to .devin/mcp_config.json
- [ ] Create profile-specific MCP configurations
- [ ] Test permission profiles
- [ ] Test lazy loading MCP servers
- [ ] Update DEVIN-SETUP-GUIDE.md with new configuration options
- [ ] Document permission profile use cases

## Expected outcomes
- **40% less** permission friction for development tasks
- **75% faster** MCP startup for simple tasks
- **30% faster** profile-specific tasks
- **Better flexibility** for different development contexts

## Risk assessment
**Medium risk** - Requires testing of permission profiles and lazy loading functionality. Changes to configuration files need careful validation to ensure backward compatibility.

## Dependencies
- Devin CLI support for permission profiles
- Devin CLI support for lazy loading MCP servers
- Testing infrastructure for configuration validation

## Related files
- `.devin/config.json`
- `.devin/mcp_config.json`
- `.devin/agents/*/config.json` (new)
- `Makefile`
- `.devin/agents/DEVIN-SETUP-GUIDE.md`
