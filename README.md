# CC-toolkits

Personal Claude Code configuration toolkit — Owen Yeh (Lenovo Firmware / OSC Compliance).

## Structure

| Directory | Contents |
|-----------|----------|
| `agents/` | 8 sub-agents (planner, python-reviewer, tdd-guide, …) |
| `skills/` | 19 skills (compliance-auditing, tdd, plan, code-review, …) |
| `rules/` | Coding style, testing, security, git-workflow |
| `hooks/` | Hook shell scripts |
| `scripts/` | Hook runner + Node.js utilities |
| `plugins/` | Marketplace plugins |
| `mcp-configs/` | MCP server configuration |
| `plans/` | Implementation plans |
| `tests/` | Script test suite |

## Deploy

```bash
git clone https://github.com/yehboy911/CC-toolkits.git
cp -r CC-toolkits/agents CC-toolkits/skills CC-toolkits/rules \
      CC-toolkits/hooks CC-toolkits/scripts CC-toolkits/plugins \
      CC-toolkits/mcp-configs ~/.claude/
```
