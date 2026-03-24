# Plan: Fix Context Exhaustion Loop in swirling-marinating-tide.md

## Context

The plan at `swirling-marinating-tide.md` has been stuck in a loop across 3+ context compaction cycles. Each session reads agent/skill files, hits context limit, compacts, and restarts at "Next: Customize all components for Owen's domain" — never completing any actual edits. This plan diagnoses the root cause and provides a fix strategy.

## Root Cause Analysis

**Primary: Monolithic Step 5 exceeds context capacity**
- Step 5 bundles ALL customization into one step: rules, hooks, mcp-configs, 8 agents, 9 skills, 10 commands, plus creating a new custom skill
- That's ~27 files to read AND edit — each agent/skill file is 86–115 lines
- Claude reads files sequentially, consuming context, and hits the limit before making any edits
- After compaction, the summary only preserves "Next: Customize all components" with no record of which files were already processed
- Result: infinite loop of read → compact → re-read → compact

**Secondary: `security-monitor` hook with `matcher: "*"`**
- Fires on EVERY tool use, adding overhead to each read/edit operation
- May contribute to "competing conversation" errors during heavy editing sessions
- Configured in `~/.claude/settings.json`

## Fix Strategy

### Step A: Decompose Step 5 into 6 atomic sub-steps

Each sub-step must be completable within a single context window (~5-8 files max per batch).

| Sub-step | Files | Est. Size |
|---|---|---|
| **5a**: Customize `rules/` files | `coding-style.md`, `testing.md`, `security.md`, `performance.md`, `patterns.md`, `git-workflow.md` | 6 files |
| **5b**: Customize agents (batch 1) | `planner`, `code-reviewer`, `python-reviewer`, `security-reviewer` | 4 files |
| **5c**: Customize agents (batch 2) | `tdd-guide`, `build-error-resolver`, `doc-updater`, `refactor-cleaner` | 4 files |
| **5d**: Customize skills | `verification-loop`, `strategic-compact`, `deep-research`, `python-testing`, `tdd`, `security`, `coding-standards`, `git-workflow` | 8 files (use subagents) |
| **5e**: Customize commands | `/plan`, `/tdd`, `/code-review`, `/e2e`, `/test-coverage`, `/quality-gate`, `/docs`, `/verify`, `/save-session`, `/resume-session` | 10 files (use subagents) |
| **5f**: Create `compliance-auditing` skill | 1 new file | 1 file |

**Key principle**: Each sub-step reads AND edits its files in one pass. No "read everything first, edit later."

### Step B: Add checkpoints to the plan

After each sub-step completes:
1. Log completion to `~/Downloads/claude-config-setup.log`
2. Update `swirling-marinating-tide.md` to mark the sub-step done
3. Run `/compact` or `/clear` to free context

### Step C: Temporarily narrow `security-monitor` hook scope

Change `matcher: "*"` to `matcher: "Bash"` in `settings.json` during the editing session to reduce per-tool-call overhead. Restore after completion.

### Step D: Use subagent delegation for bulk edits

For sub-steps 5d and 5e (8–10 files each), spawn subagents to handle batches in parallel:
- Each subagent reads 2–3 files, applies the customization pattern, saves results
- Main thread verifies and moves to next sub-step

## Execution Order

1. Apply Step C (narrow hook scope) — 1 edit to `settings.json`
2. Update `swirling-marinating-tide.md` to replace Step 5 with sub-steps 5a–5f
3. Execute sub-steps 5a → 5b → 5c → 5d → 5e → 5f sequentially, with checkpoints
4. Restore `security-monitor` hook scope
5. Continue with Steps 6–8 of original plan

## Files to Modify

- `~/.claude/settings.json` — Narrow `security-monitor` matcher temporarily
- `~/.claude/plans/swirling-marinating-tide.md` — Replace Step 5 with atomic sub-steps
- `~/.claude/rules/*.md` — Sub-step 5a (6 files)
- `~/.claude/agents/*.md` — Sub-steps 5b–5c (8 files)
- `~/.claude/skills/*.md` — Sub-step 5d (8 files)
- `~/.claude/commands/*.md` — Sub-step 5e (10 files)
- `~/.claude/skills/compliance-auditing.md` — Sub-step 5f (new file)
- `~/Downloads/claude-config-setup.log` — Checkpoint entries

## Verification

- After each sub-step: confirm files were edited (not just read) via `git diff` or `ls -la`
- After all sub-steps: run the verification from original Step 7 (test commands, verify hooks)
- Final: check `~/Downloads/claude-config-setup.log` has complete record
