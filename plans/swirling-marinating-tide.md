# Plan: Build Claude Code Configuration Architecture from everything-claude-code

## Context
Owen wants to build out an 8-directory Claude Code configuration structure under `~/.claude/`, adopting components from [everything-claude-code](https://github.com/affaan-m/everything-claude-code). This revision is based on analysis of Owen's **actual 5 projects** in `/Users/OwenYeh/Claude-workspace/projects`:

**Project profile:**
- **boost-scanner**: Python CLI scanning CMakeLists.txt for Boost dependencies → SBOM
- **osc-evidence**: Python GPL/LGPL compliance evidence generator (15 checkpoints, 3 tiers, CMake parsing)
- **OSC-workflow**: Spectra-based spec-driven development (already has `.claude/commands/spectra/` and `.claude/skills/`)
- **SBOM-Checker**: Python SBOM validation for C/C++ firmware (CSV vs source tree comparison)
- **Open-Source-Analysis**: Claude Code agentic pipeline with 5 specialized agents for end-to-end OSC auditing

**Key findings:**
- All projects are **pure Python** (stdlib only, no external deps)
- Core domain: **CMake/C/C++ firmware open-source compliance** (SBOM, GPL/LGPL)
- **No web frameworks, Docker, databases, or ML/PyTorch** in actual work
- Already using Claude Code agents in Open-Source-Analysis and Spectra commands in OSC-workflow
- **No formal test suites** in any project — TDD adoption is high value

## Target Directory: `~/.claude/`

---

### 1. `agents/` — Recommended Adoptions (8 of 28)

| Agent | Why | Project Alignment |
|---|---|---|
| `planner` | Task decomposition for multi-step compliance workflows | All projects |
| `code-reviewer` | General code review | All projects |
| `python-reviewer` | Python-specific review (all projects are Python) | All projects |
| `security-reviewer` | Security review critical for compliance/licensing work | osc-evidence, Open-Source-Analysis |
| `tdd-guide` | All 5 projects lack test suites — highest-impact addition | All projects |
| `build-error-resolver` | Auto-fix build failures in Python CLI tools | All projects |
| `doc-updater` | Auto-update docs after code changes | All projects |
| `refactor-cleaner` | Post-refactor cleanup for maturing codebases | boost-scanner, SBOM-Checker |

**Removed from initial plan:**
- ~~`architect`~~ — Projects are small CLI tools, not complex system designs
- ~~`chief-of-staff`~~ — Open-Source-Analysis already has its own orchestration; adding a generic one would conflict

**Skip:** All language-specific reviewers except Python. `loop-operator`, `harness-optimizer`, `docs-lookup` are not relevant.

---

### 2. `skills/` — Recommended Adoptions (9 of 116)

**Core workflow (keep all 3):**
- `verification-loop` — Self-verification after changes (aligns with CLAUDE.md, critical since no tests exist)
- `strategic-compact` — Context management for long compliance auditing sessions
- `deep-research` — Investigation before acting (compliance research)

**Python/Quality (revised):**
- `python-testing` — pytest patterns (all projects need tests)
- `tdd` — Test-driven development patterns (highest-impact skill)
- `security` — Security patterns for GPL/LGPL compliance auditing
- `coding-standards` — Style enforcement for Python CLI tools
- `git-workflow` — Git conventions

**Compliance-specific (new):**
- Consider creating a **custom `compliance-auditing` skill** — none exists in the repo, but Owen's domain demands one (SBOM generation, GPL/LGPL checkpoint evaluation, CMake dependency scanning)

**Removed from initial plan (not matching actual work):**
- ~~`pytorch-patterns`~~ — No ML/PyTorch in any project
- ~~`data-scraper-agent`~~ — No web scraping workflows
- ~~`docker`~~ — No containerized deployments
- ~~`api-design`~~ — CLI tools, not APIs
- ~~`database-migrations`~~ — No database usage
- ~~`cost-aware-llm-pipeline`~~ — Not relevant to compliance work
- ~~`foundation-models-on-device`~~ — Not relevant

---

### 3. `commands/` — Recommended Adoptions (10 of 59)

| Command | Purpose | Project Alignment |
|---|---|---|
| `/plan` | Generate implementation plans | All projects |
| `/tdd` | Start TDD workflow | All projects (no tests yet) |
| `/code-review` | Trigger code review | All projects |
| `/e2e` | End-to-end test runner | Open-Source-Analysis pipeline |
| `/test-coverage` | Coverage analysis | All projects |
| `/quality-gate` | Quality checks before merge | All projects |
| `/docs` | Documentation generation | All projects |
| `/verify` | Run verification suite | All projects |
| `/save-session` | Persist session state | Long compliance sessions |
| `/resume-session` | Restore session state | Long compliance sessions |

**Removed from initial plan:**
- ~~`/refactor-clean`~~ — Can use `refactor-cleaner` agent directly
- ~~`/build-fix`~~ — Can use `build-error-resolver` agent directly

**Note:** OSC-workflow already has `/spectra:*` commands (8 total). These are project-specific and should stay in that project's `.claude/commands/`, not in global `~/.claude/commands/`.

---

### 4. `hooks/` — Recommended Adoptions (7 of 17+)

**PreToolUse:**
- `security-monitor` — Flag security concerns (critical for compliance tools handling license data)
- `git-push-reminder` — Review before pushing (compliance artifacts need careful review)

**PostToolUse:**
- `quality-gate` — Auto-check quality after changes
- `python-check` — Python-specific validation (linting, type checking)

**Lifecycle:**
- `session-start` — Initialize session context
- `session-summary` — Summarize session on end (useful for compliance audit trails)

**Removed from initial plan:**
- ~~`typescript-check`~~ — No TypeScript in any project
- ~~`console-log-warning`~~ — Python projects use `print()` for CLI output; this would cause false positives
- ~~`doc-file-warning`~~ — Low value for CLI tools
- ~~`cost-tracker`~~ — Nice-to-have but not critical

---

### 5. `rules/` — Recommended Adoptions

**From `common/`:** (adopt 6 of 8)
- `coding-style.md`
- `git-workflow.md`
- `testing.md`
- `performance.md`
- `patterns.md`
- `security.md`

**Removed from common:**
- ~~`hooks.md`~~ — Will be defined by our actual hooks setup
- ~~`agents.md`~~ — Will be defined by our actual agents setup

**Language-specific:** (adopt 1)
- `python/` — Primary and only language across all projects

**Removed:**
- ~~`cpp/`~~ — Owen analyzes C/C++ code but doesn't write it; Python rules suffice

---

### 6. `mcp-configs/` — Adopt

- `mcp-servers.json` — Base MCP server configuration, customize for Owen's integrations (readiolabs.org)

---

### 7. `scripts/` — Adopt as-is

- Cross-platform Node.js utilities for hooks and setup
- Adapt for macOS/zsh environment

---

### 8. `tests/` — Adopt as-is

- Test suite for scripts and utilities from the repo

---

## Summary of Changes from Initial Plan

| Category | Initial Count | Revised Count | Key Removals | Key Additions |
|---|---|---|---|---|
| Agents | 10 | 8 | architect, chief-of-staff | — |
| Skills | 15 | 9 | pytorch, docker, api-design, database, data-scraper, cost-llm, foundation-models | Custom compliance-auditing skill |
| Commands | 12 | 10 | /refactor-clean, /build-fix | — |
| Hooks | 9 | 7 | typescript-check, console-log-warning, doc-file-warning, cost-tracker | — |
| Rules (common) | 8 | 6 | hooks.md, agents.md | — |
| Rules (lang) | 2 (python+cpp) | 1 (python) | cpp/ | — |

---

## Implementation Log Requirement

**All implementation steps and file modifications will be recorded to an external log file at:**
```
~/Downloads/claude-config-setup.log
```

This log serves as a **reproducible playbook** for setting up the same configuration on another machine. It will contain:
- Every shell command executed (with exact paths)
- Every file created or modified (with full content or diff)
- Every customization applied (with before/after)
- Verification results
- Timestamps for each step

---

## Implementation Steps

1. **Initialize log file** at `~/Downloads/claude-config-setup.log` with header and timestamp

2. **Clone the repo** to a temp location:
   ```
   git clone https://github.com/affaan-m/everything-claude-code.git /tmp/everything-claude-code
   ```

3. **Create directory structure** under `~/.claude/`:
   ```
   mkdir -p ~/.claude/{agents,skills,commands,hooks,rules,mcp-configs,scripts,tests}
   ```

4. **Copy selected components** from the cloned repo (using revised lists above) — log each file copied with source and destination paths

5. **Customize for Owen's domain** (decomposed into atomic sub-steps — complete each before starting the next):

   **5a. Customize `rules/` files** (6 files — read+edit in one pass):
   - `coding-style.md` — add pathlib preference, type hints, Python stdlib-only note
   - `testing.md` — add pytest specifics, replace generic "framework" with pytest
   - `security.md` — replace web security (SQL/XSS/CSRF) with compliance security (license scanning, SBOM integrity)
   - `performance.md` — verify model selection table is current; update Opus reference if needed
   - `patterns.md` — remove Repository Pattern and API Response Format; add compliance patterns (SBOM generation, checkpoint evaluation)
   - `git-workflow.md` — verify as-is; add note about compliance artifact commits
   - **Checkpoint**: append `[5a DONE]` to `~/Downloads/claude-config-setup.log`

   **5b. Customize agents batch 1** (4 files — read+edit in one pass):
   - `~/.claude/agents/planner.md` — add compliance workflow decomposition context
   - `~/.claude/agents/code-reviewer.md` — add Python stdlib-only, pathlib, type hints focus
   - `~/.claude/agents/python-reviewer.md` — add CMakeLists.txt parsing patterns, SBOM output validation
   - `~/.claude/agents/security-reviewer.md` — add GPL/LGPL license obligation scanning context
   - **Checkpoint**: append `[5b DONE]` to `~/Downloads/claude-config-setup.log`

   **5c. Customize agents batch 2** (4 files — read+edit in one pass):
   - `~/.claude/agents/tdd-guide.md` — add pytest, Python CLI testing patterns
   - `~/.claude/agents/build-error-resolver.md` — add Python CLI build/import error context
   - `~/.claude/agents/doc-updater.md` — add compliance doc conventions
   - `~/.claude/agents/refactor-cleaner.md` — add Python stdlib-only refactor constraints
   - **Checkpoint**: append `[5c DONE]` to `~/Downloads/claude-config-setup.log`

   **5d. Customize skills** (8 files — use subagents, 2-3 files per subagent):
   - `verification-loop`, `strategic-compact`, `deep-research`
   - `python-testing`, `tdd`, `security`, `coding-standards`, `git-workflow`
   - Each: remove web/Docker/API references, add Python CLI and compliance context
   - **Checkpoint**: append `[5d DONE]` to `~/Downloads/claude-config-setup.log`

   **5e. Customize commands** (10 files — use subagents, 3-4 files per subagent):
   - `/plan`, `/tdd`, `/code-review`, `/e2e`, `/test-coverage`
   - `/quality-gate`, `/docs`, `/verify`, `/save-session`, `/resume-session`
   - Each: remove web/Docker/API references, add Python CLI and compliance context
   - **Checkpoint**: append `[5e DONE]` to `~/Downloads/claude-config-setup.log`

   **5f. Create `compliance-auditing` skill** (1 new file):
   - `~/.claude/skills/compliance-auditing.md`
   - Content: SBOM generation workflow, GPL/LGPL 15-checkpoint evaluation, CMake dependency scanning, 3-tier evidence structure
   - **Checkpoint**: append `[5f DONE]` to `~/Downloads/claude-config-setup.log`

6. **Avoid conflicts with existing project-level configs:**
   - OSC-workflow's `.claude/commands/spectra/` and `.claude/skills/` stay project-local
   - Open-Source-Analysis's 5-agent architecture stays project-local
   - Global `~/.claude/` components should complement, not override, project-level configs

7. **Verify:**
   - Run test suite from `tests/` on macOS
   - Test `/plan`, `/tdd`, `/code-review` commands in a Claude Code session
   - Verify hooks fire correctly (especially `python-check` and `security-monitor`)
   - Run a compliance workflow end-to-end to confirm no conflicts

8. **Finalize log** — append summary and completion timestamp to the log file

## Files to Modify
- `~/.claude/settings.json` — Permission updates for new hooks/scripts
- New directories and files under `~/.claude/`
- `~/.claude/CLAUDE.md` — Already done (Task 1, no changes needed)
- `~/Downloads/claude-config-setup.log` — New: reproducible setup log for cross-machine deployment

## Notes
- before hit token limit, 5h: 95%, run /save-session
