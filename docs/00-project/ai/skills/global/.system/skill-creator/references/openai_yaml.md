# openai.yaml fields (full example + descriptions)

`agents/openai.yaml` is an extended, product-specific config intended for the machine/harness to read, not the agent. Other product-specific config can also live in the `agents/` folder.

## Full example

```yaml
interface:
  display-name: "Optional user-facing name"
  short-description: "Optional user-facing description"
  icon-small: "./assets/small-400px.png"
  icon-large: "./assets/large-logo.svg"
  brand-color: "#3B82F6"
  default-prompt: "Optional surrounding prompt to use the skill with"

dependencies:
  tools:
    - type: "mcp"
      value: "github"
      description: "GitHub MCP server"
      transport: "streamable-http"
      url: "https://api.githubcopilot.com/mcp/"

policy:
  allow-implicit-invocation: true
```

## Field descriptions and constraints

Top-level constraints:

- Quote all string values.

- Keep keys unquoted.

- For `interface.default-prompt`: generate a helpful, short (typically 1 sentence) example starting prompt based on the skill. It must explicitly mention the skill as `$skill-name` (e.g., "Use $skill-name-here to draft a concise weekly status update.").

- `interface.display-name`: Human-facing title shown in UI skill lists and chips.

- `interface.short-description`: Human-facing short UI blurb (25–64 chars) for quick scanning.

- `interface.icon-small`: Path to a small icon asset (relative to skill dir). Default to `./assets/` and place icons in the skill's `assets/` folder.

- `interface.icon-large`: Path to a larger logo asset (relative to skill dir). Default to `./assets/` and place icons in the skill's `assets/` folder.

- `interface.brand-color`: Hex color used for UI accents (e.g., badges).

- `interface.default-prompt`: Default prompt snippet inserted when invoking the skill.

- `dependencies.tools[].type`: Dependency category. Only `mcp` is supported for now.

- `dependencies.tools[].value`: Identifier of the tool or dependency.

- `dependencies.tools[].description`: Human-readable explanation of the dependency.

- `dependencies.tools[].transport`: Connection type when `type` is `mcp`.

- `dependencies.tools[].url`: MCP server URL when `type` is `mcp`.

- `policy.allow-implicit-invocation`: When false, the skill is not injected into
  the model context by default, but can still be invoked explicitly via `$skill`.
  Defaults to true.
