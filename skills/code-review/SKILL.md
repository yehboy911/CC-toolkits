---
name: code-review
description: /code-review command
origin: commands-migration
---

# Code Review

Comprehensive security and quality review of uncommitted changes:

1. Get changed files: git diff --name-only HEAD

2. For each changed file, check for:

**Security Issues (CRITICAL):**
- Hardcoded credentials, API keys, tokens
- SQL injection vulnerabilities
- XSS vulnerabilities  
- Missing input validation
- Insecure dependencies
- Path traversal risks

**Code Quality (HIGH):**
- Functions > 50 lines
- Files > 800 lines
- Nesting depth > 4 levels
- Missing error handling
- console.log statements
- TODO/FIXME comments
- Missing JSDoc for public APIs

**Best Practices (MEDIUM):**
- Mutation patterns (use immutable instead)
- Emoji usage in code/comments
- Missing tests for new code
- Accessibility issues (a11y)

3. Generate report with:
   - Severity: CRITICAL, HIGH, MEDIUM, LOW
   - File location and line numbers
   - Issue description
   - Suggested fix

4. Block commit if CRITICAL or HIGH issues found

Never approve code with security vulnerabilities!

## Owen's Domain Context (Auto-appended)
- Language: Python stdlib-only CLI tools, no web/Docker/ML/databases
- Domain: CMake/C/C++ firmware open-source compliance (SBOM, GPL/LGPL checkpoints)
- Testing: pytest (no existing suites — TDD adoption is the highest-value addition)
- Compliance artifacts require careful review before commit
- Analyze C/C++ firmware but write Python only
