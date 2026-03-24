# CC-toolkits

Personal Claude Code configuration toolkit for Owen Yeh — Lenovo Firmware / OSC Compliance Engineer.

## What's Inside

| Directory | Count | Contents |
|-----------|-------|----------|
| `agents/` | 8 | planner, code-reviewer, python-reviewer, security-reviewer, tdd-guide, build-error-resolver, doc-updater, refactor-cleaner |
| `skills/` | 19 | compliance-auditing, tdd, plan, code-review, verify, quality-gate, save-session, resume-session, deep-research, verification-loop, strategic-compact, python-testing, tdd-workflow, security-review, git-workflow, coding-standards, docs, e2e, test-coverage |
| `rules/` | 7 | coding-style, git-workflow, testing, security, performance, patterns, html-preferences (+ `python/` sub-rules) |
| `hooks/` | 6 | git-push-reminder, security-monitor, quality-gate, python-check, session-start, session-summary |
| `scripts/` | — | Hook runner (`run-with-flags.js`) + Node.js utilities |
| `plugins/` | — | Marketplace plugins |
| `mcp-configs/` | — | MCP server configuration |

## Domain Context

All agents and skills are customized for:
- **Language**: Python stdlib-only CLI tools
- **Domain**: CMake/C/C++ firmware open-source compliance (SBOM, GPL/LGPL checkpoints)
- **Testing**: pytest (TDD-first)
- No web frameworks, Docker, databases, or ML/PyTorch

## Deploy on New Machine

```bash
# 1. Clone
git clone https://github.com/yehboy911/CC-toolkits.git

# 2. Copy into ~/.claude/
cp -r CC-toolkits/agents  ~/.claude/
cp -r CC-toolkits/skills  ~/.claude/
cp -r CC-toolkits/rules   ~/.claude/
cp -r CC-toolkits/hooks   ~/.claude/
cp -r CC-toolkits/scripts ~/.claude/
cp -r CC-toolkits/plugins ~/.claude/
cp -r CC-toolkits/mcp-configs ~/.claude/

# 3. Register hooks in ~/.claude/settings.json
#    (see settings.json reference in your personal backup)
```

## Requirements

- [Claude Code](https://code.claude.com) CLI
- Node.js ≥ 18 (for hook scripts)
- Python ≥ 3.8

## License

MIT — see [LICENSE](LICENSE)
