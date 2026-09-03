# Antigravity Quick Start

## 1. Install the Foundry executable

```bash
uv tool install -e /path/to/nakeuri-flutter-foundry
```

## 2. Bootstrap a Flutter project

```bash
flutter-foundry bootstrap C:\\path\\to\\your\\flutter_project
```

This writes:

```text
<project>/.agents/mcp_config.json
<project>/.agents/plugins/nakeuri-flutter-foundry/...
<project>/PROJECT_RULES.md     # only if absent
<project>/.factory/...
```

## 3. Open the project in Antigravity

Antigravity will discover the workspace plugin and MCP definitions.

The MCP config launches:

```json
{
  "mcpServers": {
    "dart": {"command": "dart", "args": ["mcp-server"]},
    "nakeuri-flutter-foundry": {
      "command": "flutter-foundry-mcp",
      "env": {"FLUTTER_FOUNDRY_WORKSPACE": "."}
    }
  }
}
```

## 4. Confirm tools

Inside Antigravity:

- open `/mcp` and confirm both servers are healthy;
- open `/hooks` and confirm the Foundry safety hook is active;
- inspect skills and confirm Foundry workflow skills are present.

## 5. Recommended first task

Ask the agent to run discovery before making a large change:

```text
Inspect this project with the Foundry, summarize the architecture and risk surfaces, then propose only the smallest changes needed for my goal.
```

For high-risk work, ask for an isolated worktree.
