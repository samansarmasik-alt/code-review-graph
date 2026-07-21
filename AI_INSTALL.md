# ForceGraph AI installation contract

This file is written for AI coding agents. If a user asks you to integrate
ForceGraph into the repository you are currently working in, perform the steps
below instead of only explaining them.

## Goal

Install the ForceGraph CLI, configure the current AI coding platform, build the
local code graph, and verify the generated receipt. Do not report success until
the receipt says `"status": "ready"`.

## 1. Prefer automatic connection

Do not ask the user which coding tool they use unless automatic detection fails.
From the target repository root, run:

```bash
uvx --from "git+https://github.com/samansarmasik-alt/code-review-graph.git" forcegraph connect
```

This detects installed tools and also writes a vendor-neutral configuration for
unknown MCP clients. To force one environment, use the values below.

## 2. Optional explicit platform

Use the platform matching your current environment:

| Environment | Value |
|---|---|
| OpenAI Codex | `codex` |
| Claude Code | `claude-code` |
| Cursor | `cursor` |
| Windsurf | `windsurf` |
| Gemini CLI | `gemini-cli` |
| Qwen Code | `qwen` |
| Qoder | `qoder` |
| Kiro | `kiro` |
| GitHub Copilot | `copilot` |
| GitHub Copilot CLI | `copilot-cli` |
| CodeBuddy Code | `codebuddy` |
| Unknown or multiple tools | `all` |

## 3. Fallback installation

Prefer `uvx` when available:

```bash
uvx --from "git+https://github.com/samansarmasik-alt/code-review-graph.git" forcegraph connect --platform PLATFORM
```

Replace `PLATFORM` with the value selected above. If `uvx` is unavailable, use
Python 3.10 or newer:

```bash
python -m pip install "git+https://github.com/samansarmasik-alt/code-review-graph.git"
python -m code_review_graph connect --platform PLATFORM
```

On Windows, use `py` instead of `python` when that is the available launcher.

For a very large repository, `--fast` is allowed on the first run. It keeps the
structural graph and search index but skips expensive flow/community analysis.

## 4. Verify, do not guess

Read:

```text
.code-review-graph/quickstart-receipt.json
```

Success requires all of the following:

- `status` is `ready`.
- `graph.built` is `true`, unless the user explicitly requested `--no-build`.
- `graph.files` is greater than zero for a repository containing supported source files.
- The selected platform appears in `configured_platforms`, or you clearly tell
  the user that only CLI mode was configured.
- `.code-review-graph/mcp-config.json` exists when `connect` was used.

Then run:

```bash
forcegraph status
```

If the executable is not on `PATH`, use `python -m code_review_graph status`.

## 5. Hand off honestly

Tell the user:

1. Which platform was configured.
2. How many files, nodes, and edges were indexed.
3. The receipt location.
4. Whether their AI tool must be restarted to load the new MCP configuration.

After restart, call `forcegraph_context_tool` with the user's natural-language
task before broad file scanning. For parallel terminal agents, use `forcegraph_memory_tool` for bounded
decisions or handoffs. Do not ask for IDs by default; ForceGraph derives them
from session environment information and the current git branch. It selects compact search, architecture, impact,
relationship, or review context automatically. Use `detect_changes_tool` only
when a deeper risk review is needed.

## Safety rules

- Do not upload the user's source code; the graph is local-first.
- Do not print secrets found in configuration files.
- Do not overwrite unrelated MCP servers, hooks, or instruction content.
- Stop and report the exact error if installation or graph building fails.
- Never claim the integration is active when a required restart is still pending.
