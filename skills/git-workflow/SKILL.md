---
name: git-workflow
description: Use this skill for all git operations in firmware open-source compliance projects. Enforces conventional commits for compliance artifacts, branch naming for SBOM/audit work, and review requirements for GPL/LGPL changes.
origin: custom
---

# Git Workflow for Firmware Compliance

## When to Activate

- Before any `git commit` in a compliance or SBOM project
- When creating branches for audit, compliance review, or SBOM generation work
- When pushing changes that touch GPL/LGPL license analysis or CMake dependency scanning
- When reviewing or preparing PRs for compliance artifacts

## Core Principles

### 1. Commit Types for Compliance Work

Standard types plus compliance-domain extensions:

| Type | Use For |
|---|---|
| `feat` | New compliance check, new SBOM field, new audit checkpoint |
| `fix` | Bug in detection logic, incorrect license classification |
| `refactor` | Code restructure without behavior change |
| `test` | New or updated test cases |
| `docs` | README, compliance report templates, checkpoint docs |
| `chore` | Dependency updates, config changes, tooling |
| `perf` | Performance improvements (scan speed, CMake parsing) |
| `ci` | CI/CD pipeline changes |
| `compliance` | Changes to license classification rules or GPL/LGPL logic |
| `sbom` | Changes to SBOM output format, fields, or generation |
| `audit` | Checkpoint updates, evidence collection changes, tier logic |

### 2. Branch Naming Conventions

Format: `<category>/<short-description>`

| Category | Examples |
|---|---|
| `compliance/` | `compliance/lgpl-detection-v2`, `compliance/cmake-boost-scan` |
| `sbom/` | `sbom/add-license-field`, `sbom/csv-export-format` |
| `audit/` | `audit/checkpoint-15-evidence`, `audit/tier2-review` |
| `fix/` | `fix/false-positive-gpl`, `fix/cmake-parse-error` |
| `feat/` | `feat/sbom-checker-html-report`, `feat/boost-version-detect` |
| `refactor/` | `refactor/osc-evidence-paths`, `refactor/sbom-validator` |
| `test/` | `test/unit-license-classifier`, `test/integration-cmake-parser` |

### 3. Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer: refs #issue, BREAKING CHANGE: ...]
```

Scope examples: `boost-scanner`, `osc-evidence`, `sbom-checker`, `cmake-parser`, `license-classifier`, `checkpoint`, `report`

**Compliance-specific body guidance:**
- For GPL/LGPL changes: note which packages are affected and classification rationale
- For SBOM format changes: note schema version and field impact
- For checkpoint changes: reference checkpoint number (e.g., `CP-08`, `CP-15`) and tier

**Example commits:**
```
compliance(license-classifier): add LGPL-2.1-only detection for linked libs

Distinguish between LGPL-2.1-or-later and LGPL-2.1-only in static linking
scenarios. Affects tier-2 evidence collection for CP-07 and CP-08.

Refs: osc-evidence#42
```

```
sbom(csv-export): add component hash field per NTIA minimum elements

SHA-256 hash column required for NTIA SBOM minimum elements compliance.
Updates both generation (boost-scanner) and validation (sbom-checker).
```

```
audit(checkpoint): update CP-15 evidence template for XCC firmware

Add XCC-specific binary scan output format to CP-15 evidence collector.
Tier-3 only — does not affect tier-1 or tier-2 evidence.
```

## Git Workflow Steps

### Step 1: Branch Before Work

Always branch from `main` (or project default) before starting compliance work:

```bash
git checkout main && git pull
git checkout -b compliance/your-work-description
```

### Step 2: Incremental Commits During Work

Commit logically related changes together. For compliance projects:
- One commit per checkpoint change
- One commit per SBOM field addition
- Keep license classification changes separate from output format changes

### Step 3: Pre-Push Checklist

Before pushing compliance artifact changes:
- [ ] No hardcoded absolute paths (use `pathlib.Path` / relative paths)
- [ ] No real customer SBOM data or firmware binary paths in committed files
- [ ] License classification logic changes have corresponding test coverage
- [ ] `python3 -m py_compile <changed_files>` passes (or run `python3 -c "import <module>"`)
- [ ] If GPL/LGPL logic changed: confirm no false positives on known-good test fixtures

### Step 4: PR Description for Compliance Work

Structure PR body as:
```
## Summary
- What changed and why (1-3 bullets)

## Compliance Impact
- Which checkpoints (CP-XX) are affected
- Which tier(s) (1/2/3) are affected
- Any change to SBOM output format or fields

## Test Plan
- [ ] Unit tests pass
- [ ] Tested against: [specific firmware/project name]
- [ ] No regressions in known-good fixtures
```

### Step 5: Merge Strategy

- **Squash merge** for feature branches with many WIP commits
- **Merge commit** for branches with meaningful commit history (audit trails for compliance work)
- **Never force-push** to `main` or `master` — compliance artifact history must be preserved

## Owen's Domain Context (Auto-appended)
- Language: Python stdlib-only CLI tools, no web/Docker/ML/databases
- Domain: CMake/C/C++ firmware open-source compliance (SBOM, GPL/LGPL checkpoints)
- Testing: pytest (no existing suites — TDD adoption is the highest-value addition)
- Compliance artifacts require careful review before commit
- Analyze C/C++ firmware but write Python only
