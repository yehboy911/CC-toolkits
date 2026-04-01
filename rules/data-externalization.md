# Data Externalization — Single Source of Truth

## Core Principle

**Disk is truth. Conversation memory is not.**

Anything that matters MUST exist as a file on disk — not just in the context window.
If it's not on disk, it doesn't exist.

## Mandatory: Always Write to Disk

ALL of the following MUST be saved to disk immediately upon creation or update:

| Artifact | Default Path | Format |
|---|---|---|
| Plan | `./plan.md` or `/tmp/<task>/plan.md` | Markdown |
| TODO list | `./todo.md` or `/tmp/<task>/todo.md` | Markdown checklist |
| Progress log | `./progress.log` or `/tmp/<task>/progress.log` | Append-only timestamped lines |
| Decision log | `./decisions.md` | Markdown ADR-style entries |
| Session state | `~/.claude/sessions/<date>.md` | Use `/save-session` skill |

## Rules

1. **Write before acting** — save the plan/todo BEFORE starting implementation.
2. **Append, never overwrite logs** — progress.log entries are append-only.
3. **Reference by path** — always tell the user the file path: `"Plan saved to ./plan.md"`.
4. **No in-memory-only state** — never hold task state solely in conversation memory.
5. **Update on change** — if the plan or todo changes mid-task, update the file immediately.
6. **Completion = disk sync** — a task is not "done" until all artifacts are flushed to disk.

## Enforcement

Before starting any non-trivial task (more than 1 file changed or more than 3 steps):

```
[ ] plan.md written
[ ] todo.md written (with checkboxes)
[ ] progress.log initialized
```

After completing each subtask:

```
[ ] todo.md checkbox ticked
[ ] progress.log entry appended with timestamp
```

## Progress Log Format

```
[YYYY-MM-DD HH:MM] STARTED  <task name>
[YYYY-MM-DD HH:MM] DONE     <subtask>
[YYYY-MM-DD HH:MM] BLOCKED  <blocker description>
[YYYY-MM-DD HH:MM] COMPLETE <task name>
```

## Why

- Context windows are ephemeral — compaction wipes in-memory state silently.
- Disk files survive `/clear`, session restarts, and model switches.
- Future sessions (and subagents) can resume from disk without re-explaining context.
- Enables parallel subagents to share state via filesystem without race conditions.

## Owen's Domain Context (Auto-appended)
- Language: Python stdlib-only CLI tools, no web/Docker/ML/databases
- Domain: CMake/C/C++ firmware open-source compliance (SBOM, GPL/LGPL checkpoints)
- Testing: pytest (no existing suites — TDD adoption is the highest-value addition)
- Compliance artifacts require careful review before commit
- Analyze C/C++ firmware but write Python only
