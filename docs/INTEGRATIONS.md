# Universal AI tool integration

ForceGraph uses the open Model Context Protocol (MCP). It does not require
ForceCLI, ForceCode, or any other Force product.

## Recommended installation

Run this from the repository you want an AI tool to understand:

```bash
uvx --from "git+https://github.com/samansarmasik-alt/code-review-graph.git" forcegraph connect
```

The command performs four idempotent steps:

1. detects locally installed AI coding tools;
2. merges an MCP server entry without replacing unrelated settings;
3. builds the local structural graph;
4. writes a receipt and a vendor-neutral MCP configuration.

The generated MCP command starts with `--auto-watch`. After the one-time
connection, the graph follows file changes for as long as the AI client is
running; users do not need to manage build, update, or watch commands.

It also starts with `--tool-profile compact`. The agent sees only the nine
high-value tools required for orientation, search, relationships, impact,
review, architecture, traversal, and graph refresh. This avoids repeatedly
sending the schemas of rarely used administration and analysis tools. Run
`forcegraph serve --tool-profile full` only for advanced manual workflows.

Use `--dry-run` to preview files, `--fast` for a large first build, or
`--platform NAME` to target one client explicitly.

If this fork is mirrored, set `FORCEGRAPH_UVX_SOURCE` to the mirror's package or
Git URL before connecting. Generated MCP entries will keep using that source.

## Supported clients

| Client | Target | Configuration |
| --- | --- | --- |
| OpenAI Codex | `codex` | `~/.codex/config.toml` |
| Claude Code | `claude-code` | `.mcp.json` |
| Cursor | `cursor` | `.cursor/mcp.json` |
| Windsurf | `windsurf` | `~/.codeium/windsurf/mcp_config.json` |
| Zed | `zed` | platform Zed settings |
| Continue | `continue` | `~/.continue/config.json` |
| OpenCode | `opencode` | `opencode.jsonc` |
| Gemini CLI | `gemini-cli` | `.gemini/settings.json` |
| Qwen Code | `qwen` | `~/.qwen/settings.json` |
| Qoder | `qoder` | `.qoder/mcp.json` |
| Kiro | `kiro` | `.kiro/settings/mcp.json` |
| GitHub Copilot | `copilot` | `.vscode/mcp.json` |
| GitHub Copilot CLI | `copilot-cli` | `~/.copilot/mcp-config.json` |
| CodeBuddy | `codebuddy` | `.mcp.json` |

## Any other MCP client

After `connect`, read:

```text
.code-review-graph/mcp-config.json
```

The `mcpServers.code-review-graph` value contains a ready stdio server entry.
Copy it into the equivalent MCP server section of the client. The file is
generated locally because its `cwd` is specific to the current checkout.

## Verification contract

`.code-review-graph/quickstart-receipt.json` must contain `"status": "ready"`.
For a non-empty supported repository, `graph.files` should be greater than zero.
Restart clients listed in `configured_platforms`, then ask the agent to inspect
architecture or impact through ForceGraph before broadly reading source files.

Neither the graph database nor generated connection files should be committed;
they are local machine state and are already covered by `.gitignore`.
