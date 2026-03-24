#!/usr/bin/env node
/**
 * Python Check Hook (PostToolUse)
 *
 * Validates Python syntax after .py file edits using py_compile.
 * Zero external dependencies — uses the system python3.
 *
 * Compatible with run-with-flags.js fast path (exports { run }).
 * Logs warnings to stderr on syntax errors, never blocks.
 * Set ECC_PYTHON_CHECK_STRICT=true to block on syntax errors (exit 2).
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const MAX_STDIN = 1024 * 1024;

/**
 * @param {string} msg
 */
function log(msg) {
  process.stderr.write(`[PythonCheck] ${msg}\n`);
}

/**
 * Run python3 -c py_compile on a file.
 *
 * @param {string} filePath - Absolute path to .py file
 * @returns {{ ok: boolean, error: string }}
 */
function checkSyntax(filePath) {
  const result = spawnSync('python3', [
    '-c',
    `import py_compile; py_compile.compile(${JSON.stringify(filePath)}, doraise=True)`
  ], {
    encoding: 'utf8',
    timeout: 10000,
    env: process.env,
  });

  if (result.error) {
    // python3 not found or timeout — skip silently
    return { ok: true, error: '' };
  }

  if (result.status !== 0) {
    const msg = (result.stderr || result.stdout || '').trim();
    return { ok: false, error: msg };
  }

  return { ok: true, error: '' };
}

/**
 * Core logic — exported for run-with-flags.js fast path.
 *
 * @param {string} rawInput - Raw JSON string from stdin
 * @returns {string} The original input (pass-through)
 */
function run(rawInput) {
  try {
    const data = JSON.parse(rawInput);
    const toolInput = data.tool_input || {};

    // Extract file path from Edit, Write, or MultiEdit
    let filePath = String(toolInput.file_path || '');

    if (!filePath) {
      return rawInput;
    }

    // Only check .py files
    if (path.extname(filePath).toLowerCase() !== '.py') {
      return rawInput;
    }

    // Resolve to absolute
    filePath = path.resolve(filePath);

    // File must exist
    if (!fs.existsSync(filePath)) {
      return rawInput;
    }

    const { ok, error } = checkSyntax(filePath);

    if (ok) {
      return rawInput;
    }

    const strict = String(process.env.ECC_PYTHON_CHECK_STRICT || '').toLowerCase() === 'true';

    if (strict) {
      process.stdout.write(`[PythonCheck] Syntax error in ${filePath}:\n${error}\n`);
      process.exit(2);
    }

    log(`Syntax warning for ${filePath}:\n${error}`);

  } catch {
    // Ignore parse errors — pass through
  }

  return rawInput;
}

// ── stdin entry point (backwards-compatible) ────────────────────
if (require.main === module) {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => {
    if (raw.length < MAX_STDIN) {
      const remaining = MAX_STDIN - raw.length;
      raw += chunk.substring(0, remaining);
    }
  });

  process.stdin.on('end', () => {
    const result = run(raw);
    process.stdout.write(result);
  });
}

module.exports = { run };
