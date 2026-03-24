# Testing Requirements

## Minimum Test Coverage: 80%

Test Types (ALL required):
1. **Unit Tests** - Individual functions, utilities, components
2. **Integration Tests** - API endpoints, database operations
3. **E2E Tests** - Critical user flows (framework chosen per language)

## Test-Driven Development

MANDATORY workflow:
1. Write test first (RED)
2. Run test - it should FAIL
3. Write minimal implementation (GREEN)
4. Run test - it should PASS
5. Refactor (IMPROVE)
6. Verify coverage (80%+)

## Troubleshooting Test Failures

1. Use **tdd-guide** agent
2. Check test isolation
3. Verify mocks are correct
4. Fix implementation, not tests (unless tests are wrong)

## Agent Support

- **tdd-guide** - Use PROACTIVELY for new features, enforces write-tests-first

## Owen's Domain Context (Auto-appended)
- Language: Python stdlib-only CLI tools, no web/Docker/ML/databases
- Domain: CMake/C/C++ firmware open-source compliance (SBOM, GPL/LGPL checkpoints)
- Testing: pytest (no existing suites — TDD adoption is the highest-value addition)
- Compliance artifacts require careful review before commit
- Analyze C/C++ firmware but write Python only
